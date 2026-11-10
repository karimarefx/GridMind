"""Loopback-only upload PoC. Run: python -m gridmind.api."""
from contextlib import asynccontextmanager
import csv
import importlib.metadata
import io
import json
from pathlib import Path
import tempfile

import joblib
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .diagnosis import sha256
from .diagnosis_context import CONTEXT_FEATURES
from .stage1 import VERSION, predict

ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / "models/stage1"
MAX_BYTES = 2 * 1024 * 1024
COLUMNS = ["elapsed_seconds", "angle", "reconstructed", "frequency", "voltage_magnitude", "current_magnitude", "current_angle"]


def load_model(directory):
    manifest = json.loads((directory / "deployment_manifest.json").read_text())
    path = directory / "model.joblib"
    if sha256(path) != manifest["model_sha256"]:
        raise ValueError("Packaged model checksum mismatch")
    if manifest["sklearn_version"] != importlib.metadata.version("scikit-learn"):
        raise ValueError("Model requires its recorded scikit-learn version")
    bundle = joblib.load(path)  # Only the pinned, packaged local file, never an upload.
    if bundle["version"] != VERSION or bundle["features"] != CONTEXT_FEATURES or bundle["profile"] != "measurement-context":
        raise ValueError("Unsupported model schema")
    return bundle


def infer_bytes(bundle, payload, unit):
    if unit not in {"degree", "radian"}:
        raise ValueError("Angle unit must be degree or radian")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError as error:
        raise ValueError("CSV must use UTF-8 text") from error
    header = next(csv.reader(io.StringIO(text)), [])
    if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
        raise ValueError("CSV requires exactly these columns: " + ", ".join(COLUMNS))
    with tempfile.TemporaryDirectory(prefix="gridmind-upload-") as folder:
        path = Path(folder) / "window.csv"
        path.write_bytes(payload)
        result, trace = predict(bundle, path, unit)
    return {"prediction": result, "trace": trace[COLUMNS].to_dict(orient="records"), "angle_unit": unit,
            "input_origin": "uploaded; ground truth not supplied"}


def create_app(model_directory=MODEL_ROOT, dist=ROOT / "frontend/dist"):
    @asynccontextmanager
    async def lifespan(app):
        app.state.bundle = None
        app.state.model_error = None
        try:
            app.state.bundle = load_model(Path(model_directory))
        except Exception:
            app.state.model_error = "Stage 1 bundle unavailable or incompatible. Check the packaged model and recorded dependencies."
        yield

    app = FastAPI(title="GridMind local Stage 1 PoC", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def limit_body(request, call_next):
        if request.url.path == "/api/diagnosis":
            total = 0
            body = bytearray()
            async for chunk in request.stream():
                total += len(chunk)
                if total > MAX_BYTES + 65536:
                    return JSONResponse({"detail": "Upload exceeds the 2 MiB file limit."}, status_code=413)
                body.extend(chunk)
            # Cache the bounded multipart body for the framework's form parser.
            request._body = bytes(body)
        return await call_next(request)

    @app.get("/api/health")
    def health():
        ready = app.state.bundle is not None
        return JSONResponse({"ready": ready, "model_version": VERSION if ready else None,
                             "experimental": True, "reason": app.state.model_error}, status_code=200 if ready else 503)

    @app.get("/api/evaluation")
    def evaluation():
        path = Path(model_directory) / "evaluation.json"
        if not path.is_file():
            raise HTTPException(503, "Measured pipeline evaluation unavailable")
        return json.loads(path.read_text())

    @app.post("/api/diagnosis")
    async def diagnosis(file: UploadFile = File(...), angle_unit: str = Form("degree")):
        try:
            if app.state.bundle is None:
                raise HTTPException(503, app.state.model_error)
            payload = await file.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise HTTPException(413, "Upload exceeds the 2 MiB file limit.")
            return await run_in_threadpool(infer_bytes, app.state.bundle, payload, angle_unit)
        except (ValueError, TypeError, KeyError) as error:
            raise HTTPException(422, str(error)) from error
        finally:
            await file.close()

    @app.api_route("/api/{path:path}", methods=["GET", "POST"])
    def unknown_api(path: str):
        raise HTTPException(404, "Unknown API route")

    if Path(dist).is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
    else:
        @app.get("/")
        def no_frontend():
            return JSONResponse({"detail": "Build the dashboard first: cd frontend; npm ci; npm run build"}, status_code=503)
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, access_log=False)
