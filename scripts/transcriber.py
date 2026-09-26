import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--model', default=os.getenv('WHISPER_MODEL', 'small'))
    args = parser.parse_args()
    if not args.input or not args.output:
        print('Transcriber: skipped; no input/output.')
        return
    source = Path(args.input)
    output = Path(args.output)
    if not source.exists():
        raise SystemExit(f'Input does not exist: {source}')
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit('faster-whisper is not installed') from exc
    device = os.getenv('WHISPER_DEVICE', 'cpu')
    compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'int8' if device == 'cpu' else 'float16')
    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(source), language='es', beam_size=5, word_timestamps=True, vad_filter=True)
    result = []
    for segment in segments:
        result.append({'start': float(segment.start), 'end': float(segment.end), 'text': segment.text.strip(), 'words': [
            {'start': float(w.start), 'end': float(w.end), 'text': w.word, 'probability': float(w.probability)}
            for w in (segment.words or [])
        ]})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'schema_version':1,'source':str(source),'language':info.language,'language_probability':info.language_probability,'segments':result}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Transcriber: {len(result)} segments written')


if __name__ == '__main__':
    main()
