from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path

try:
    from space_automation.apod_client import download_apod_image, fetch_apod
    from space_automation.config import get_space_automation_config
    from space_automation.editor import render_short_video
    from space_automation.producer import generate_producer_output
    from space_automation.subtitles import write_srt
    from space_automation.tts import synthesize_speech_to_mp3
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from apod_client import download_apod_image, fetch_apod
    from config import get_space_automation_config
    from editor import render_short_video
    from producer import generate_producer_output
    from subtitles import write_srt
    from tts import synthesize_speech_to_mp3


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _create_job_dir(output_dir: Path) -> Path:
    job_dir = output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_dir


def _base_run_state(job_dir: Path) -> dict:
    return {
        "status": "running",
        "current_step": "bootstrap",
        "job_dir": str(job_dir),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
        "error": None,
        "artifacts": {},
    }


def main() -> int:
    config = get_space_automation_config()
    job_dir = _create_job_dir(config.output_dir)
    run_state = _base_run_state(job_dir)
    run_state_path = job_dir / "run.json"
    _write_json(run_state_path, run_state)

    try:
        run_state["current_step"] = "fetch_apod"
        _write_json(run_state_path, run_state)
        apod = fetch_apod(config)
        _write_json(job_dir / "apod.json", apod.to_dict())
        run_state["artifacts"]["apod_json"] = str(job_dir / "apod.json")

        if apod.media_type.lower() != "image":
            run_state["status"] = "skipped"
            run_state["current_step"] = "done"
            run_state["error"] = f"APOD media_type '{apod.media_type}' is not supported."
            run_state["finished_at"] = datetime.now().isoformat(timespec="seconds")
            _write_json(run_state_path, run_state)
            return 0

        run_state["current_step"] = "download_image"
        _write_json(run_state_path, run_state)
        image_path = download_apod_image(apod, config, job_dir)
        run_state["artifacts"]["image"] = str(image_path)

        run_state["current_step"] = "producer"
        _write_json(run_state_path, run_state)
        producer_output = generate_producer_output(
            config=config,
            title=apod.title,
            explanation=apod.explanation,
        )
        script_path = job_dir / "script.txt"
        script_path.write_text(producer_output.script.strip() + "\n", encoding="utf-8")
        producer_path = job_dir / "producer.json"
        _write_json(producer_path, producer_output.to_dict())
        run_state["artifacts"]["script"] = str(script_path)
        run_state["artifacts"]["producer_json"] = str(producer_path)

        run_state["current_step"] = "tts"
        _write_json(run_state_path, run_state)
        tts_output = synthesize_speech_to_mp3(
            producer_output.script,
            job_dir / "voice.mp3",
            config,
        )
        tts_path = job_dir / "tts.json"
        _write_json(tts_path, tts_output.to_dict())
        run_state["artifacts"]["voice_mp3"] = tts_output.audio_path
        run_state["artifacts"]["tts_json"] = str(tts_path)
        run_state["artifacts"]["audio_duration_seconds"] = tts_output.duration_seconds

        run_state["current_step"] = "subtitles"
        _write_json(run_state_path, run_state)
        subtitle_path = job_dir / "subtitles.srt"
        subtitle_segments = write_srt(
            producer_output.script,
            tts_output.duration_seconds,
            subtitle_path,
        )
        run_state["artifacts"]["subtitles_srt"] = str(subtitle_path)
        run_state["artifacts"]["subtitle_segments"] = len(subtitle_segments)

        run_state["current_step"] = "render"
        _write_json(run_state_path, run_state)
        render_output = render_short_video(
            config=config,
            image_path=image_path,
            audio_path=Path(tts_output.audio_path),
            control=producer_output.control,
            subtitle_segments=subtitle_segments,
            duration_seconds=tts_output.duration_seconds,
            output_path=job_dir / "final.mp4",
        )
        render_path = job_dir / "render.json"
        _write_json(render_path, render_output.to_dict())
        run_state["artifacts"]["final_mp4"] = render_output.output_path
        run_state["artifacts"]["render_json"] = str(render_path)

        run_state["status"] = "success"
        run_state["current_step"] = "done"
        run_state["finished_at"] = datetime.now().isoformat(timespec="seconds")
        _write_json(run_state_path, run_state)
        return 0
    except Exception as exc:
        run_state["status"] = "failed"
        run_state["finished_at"] = datetime.now().isoformat(timespec="seconds")
        run_state["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        _write_json(run_state_path, run_state)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
