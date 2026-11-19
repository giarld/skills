#!/usr/bin/env python3
"""MiniMax H3 with an environment-configurable API base. Python 3 standard library only."""
import argparse
import ipaddress
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = 'https://api.minimax.cn/v2'
BASE_ENV = 'VIDEOGEN_H3_API_BASE_URL'
KEY_ENV = 'VIDEOGEN_H3_API_KEY'
RATIOS = {'adaptive', '21:9', '16:9', '4:3', '1:1', '3:4', '9:16'}
MODEL_LIMITS = {
    'MiniMax-H3': (('768P', '2K'), 4),
    'MiniMax-H3-Highspeed': (('480P', '768P'), 4),
    'MiniMax-H3-Lite': (('480P', '768P'), 4),
    'MiniMax-H3-Max': (('480P', '768P'), 5),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def api_base():
    value = os.environ.get(BASE_ENV, DEFAULT_BASE).strip().rstrip('/')
    parsed = urllib.parse.urlsplit(value)
    require(parsed.scheme in ('http', 'https') and parsed.hostname
            and parsed.username is None and parsed.password is None
            and '?' not in value and '#' not in value and not any(c.isspace() for c in value),
            BASE_ENV + ' must be a nonempty HTTP(S) base URL without credentials, query or fragment')
    require(parsed.port is None or parsed.port > 0, 'Invalid API port')
    require(parsed.scheme == 'https' or loopback(parsed.hostname), 'Remote API bases must use HTTPS')
    return value


def validate(body, regen=False):
    require(isinstance(body, dict), 'Request must be a JSON object')
    model = body.get('model')
    require(isinstance(model, str) and model in MODEL_LIMITS, 'Use a supported MiniMax H3 model ID')
    if 'generate_audio' in body:
        require(type(body['generate_audio']) is bool, 'generate_audio must be a boolean')
    if regen:
        require(model == 'MiniMax-H3' and body.get('resolution') == '2K', 'Regeneration requires MiniMax-H3 and 2K')
        require('duration' not in body and 'ratio' not in body, 'Regeneration does not accept duration or ratio')
        require(('source_task_id' in body) != ('content' in body), 'Provide exactly one of source_task_id or content')
        if 'source_task_id' in body:
            require(isinstance(body['source_task_id'], str) and body['source_task_id'].strip(), 'Empty source_task_id')
            return
    else:
        resolutions, minimum_duration = MODEL_LIMITS[model]
        require(body.get('resolution') in resolutions, 'Unsupported resolution for model')
        duration = body.get('duration')
        require(type(duration) is int and minimum_duration <= duration <= 15, 'Invalid integer duration')
        require(isinstance(body.get('ratio', 'adaptive'), str) and body.get('ratio', 'adaptive') in RATIOS, 'Invalid ratio')
        if 'extra' in body:
            extra = body['extra']
            require(model == 'MiniMax-H3-Max' and isinstance(extra, dict), 'extra is only supported by Max')
            require(set(extra) <= {'prompt_expansion_mode'} and extra.get('prompt_expansion_mode', 'balanced') in ('disabled', 'balanced', 'quality'), 'Invalid extra')
    content = body.get('content')
    require(isinstance(content, list) and content, 'content must be a nonempty array')
    roles = []
    texts = 0
    for item in content:
        require(isinstance(item, dict), 'Each content item must be an object')
        kind = item.get('type')
        require(kind in ('text', 'image_url', 'video_url', 'audio_url'), 'Invalid content type')
        if kind == 'text':
            value = item.get('text')
            require(isinstance(value, str) and value.strip() and len(value) <= (40000 if regen else 7000), 'Invalid prompt length')
            texts += 1
            continue
        media = item.get(kind)
        require(isinstance(media, dict) and isinstance(media.get('url'), str), 'Media needs a nested url object')
        url = media['url']
        require(url.startswith(('https://', 'http://', 'mm_file://', 'data:')), 'Media must be an accessible URL, platform file or data URI')
        role = item.get('role', 'first_frame' if kind == 'image_url' else None)
        allowed = {'image_url': {'first_frame', 'last_frame', 'reference_image'}, 'video_url': {'reference_video'} | ({'base_video'} if regen else set()), 'audio_url': {'reference_audio'}}
        require(role in allowed[kind], 'Invalid media role for type')
        roles.append(role)
    require(texts > 0, 'A nonempty text prompt is required')
    require(not (set(roles) & {'first_frame', 'last_frame'} and set(roles) & {'reference_image', 'reference_video', 'reference_audio'}), 'Frame images and multimodal references cannot be mixed')
    for role, limit in [('first_frame', 1), ('last_frame', 1), ('reference_image', 9), ('reference_video', 3), ('reference_audio', 3)]:
        require(roles.count(role) <= limit, 'Too many ' + role)
    if regen:
        require(roles.count('base_video') == 1, 'Regeneration requires exactly one base_video')
    elif not roles:
        require(len(content) == 1 and body.get('ratio') in RATIOS - {'adaptive'}, 'Text-only generation needs one text and an explicit ratio')
    elif model == 'MiniMax-H3-Lite' and set(roles) & {'reference_image', 'reference_video', 'reference_audio'}:
        require(body.get('ratio', 'adaptive') != 'adaptive', 'Lite reference generation requires an explicit non-adaptive ratio')


def json_payload(body):
    return json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')


def request(method, path, body=None):
    key = os.environ.get(KEY_ENV, '').strip()
    require(key and not any(c.isspace() for c in key), 'Set ' + KEY_ENV + ' in the execution environment')
    data = None if body is None else json_payload(body)
    req = urllib.request.Request(api_base() + path, data=data, method=method, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    # Do not redirect authenticated API requests to another origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            failure = json.loads(exc.read())
            detail = failure.get('error', {})
            message = str(detail.get('message', ''))[:1000].replace(key, '[REDACTED]')
            request_id = str(failure.get('request_id', ''))[:200].replace(key, '[REDACTED]')
        except (ValueError, AttributeError):
            message, request_id = '', ''
        raise RuntimeError(f'API HTTP {exc.code}: {message}; request_id={request_id}') from None
    require(isinstance(result, dict) and result.get('type') != 'error', 'API returned an error response')
    return result


def query(task_id):
    require(task_id and task_id.strip(), 'task-id cannot be empty')
    return request('GET', '/query/video_generation/' + urllib.parse.quote(task_id, safe=''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for mode in ('create', 'regenerate'):
        p = sub.add_parser(mode)
        p.add_argument('--json', required=True, type=Path)
        p.add_argument('--dry-run', action='store_true')
    for mode in ('query', 'wait', 'download'):
        p = sub.add_parser(mode)
        p.add_argument('--task-id', required=True)
        if mode == 'wait':
            p.add_argument('--timeout', type=float, default=900)
            p.add_argument('--interval', type=float, default=15)
        if mode == 'download':
            p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.command in ('create', 'regenerate'):
        body = json.loads(args.json.read_text(encoding='utf-8'))
        require(len(json_payload(body)) <= 64 * 1024 * 1024, 'Request exceeds 64 MiB')
        validate(body, args.command == 'regenerate')
        path = '/video_generation' if args.command == 'create' else '/video_regeneration'
        if args.dry_run:
            result = {'method': 'POST', 'url': api_base() + path, 'model': body['model'], 'resolution': body['resolution'], 'content_items': len(body.get('content', [])), 'uses_source_task': 'source_task_id' in body}
        else:
            result = request('POST', path, body)
            require(result.get('task_id'), 'Create response has no task_id; do not automatically resubmit')
    elif args.command == 'wait':
        require(all(math.isfinite(value) and value > 0 for value in (args.timeout, args.interval)),
                'timeout and interval must be positive and finite')
        deadline = time.monotonic() + args.timeout
        while True:
            result = query(args.task_id)
            task = result.get('task', {})
            status = task.get('status')
            require(status in ('queued', 'running', 'succeeded', 'failed', 'cancelled'), 'Unknown task status')
            if status in ('succeeded', 'failed', 'cancelled'):
                break
            if time.monotonic() >= deadline:
                result['wait_timeout'] = True
                break
            print(json.dumps({'task_id': args.task_id, 'status': status}), file=sys.stderr, flush=True)
            time.sleep(max(0, min(args.interval, deadline - time.monotonic())))
    else:
        result = query(args.task_id)
        if args.command == 'download':
            task = result.get('task', {})
            require(task.get('status') == 'succeeded', 'Task has not succeeded')
            url = task.get('content', {}).get('url', '')
            require(url.startswith(('https://', 'http://')), 'Missing HTTP video URL')
            output = args.output.expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation avoids clobbering a user file. No auth header goes to CDN.
            with output.open('xb') as dest:
                try:
                    with urllib.request.urlopen(url, timeout=60) as source:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            dest.write(chunk)
                except Exception:
                    output.unlink(missing_ok=True)
                    raise
            result = {'task_id': args.task_id, 'output': str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command in ('query', 'wait') and result.get('task', {}).get('status') in ('failed', 'cancelled'):
        return 1
    if result.get('wait_timeout'):
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        sys.exit(1)
