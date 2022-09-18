import uvicorn
import odrpc
import base64
import logging
import asyncio
from fastapi import status, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from concurrent.futures import ThreadPoolExecutor


class API():
    def __init__(self, config, doods):
        self.config = config
        self.doods = doods
        self.api = FastAPI()
        # Borrow the uvicorn logger because it's pretty.
        self.logger = logging.getLogger("doods.api")

        @self.api.get("/detectors", response_model=odrpc.DetectorsResponse, response_model_exclude_none=True)
        async def detectors():
            return odrpc.DetectorsResponse(detectors=self.doods.detectors())

        @self.api.post("/detect", response_model=odrpc.DetectResponse, response_model_exclude_none=True)
        async def detect(detect_request: odrpc.DetectRequest, response: Response):
            # logger.info('detect request: %s', detect_request)
            detect_response = self.doods.detect(detect_request)
            if detect_response.error:
                response.status_code = status.HTTP_400_BAD_REQUEST
            # If we requested an image, base64 encode it back to the user
            if detect_request.image:
                detect_response.image = base64.b64encode(detect_response.image)
            return detect_response
        
        @self.api.websocket("/detect")
        async def detect_stream(websocket: WebSocket):
            await websocket.accept()
            detect_responses = asyncio.Queue()
            executor = ThreadPoolExecutor()
            async def detect_handle(detect_request: odrpc.DetectRequest):
                try:
                    detect_response = self.doods.detect(detect_request)
                    if detect_request.image:
                        detect_response.image = base64.b64encode(detect_response.image)
                    await detect_responses.put(detect_response)
                except asyncio.TimeoutError:
                    self.logger.error("Detector timeout error")
                except Exception as e:
                    self.logger.error("Exception({0}):{1!r}".format(type(e).__name__, e.args))

            def detect_thread(detect_request: odrpc.DetectRequest):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(detect_handle(detect_request))
                    loop.close()
                except Exception as e:
                    self.logger.error("Exception({0}):{1!r}".format(type(e).__name__, e.args))
                    loop.close()

            async def send_detect_responses():
                try:
                    while True:
                        detect_response = await detect_responses.get()
                        await websocket.send_json(detect_response.asdict(include_none=False))
                except Exception as e:
                    self.logger.error("Exception({0}):{1!r}".format(type(e).__name__, e.args))

            send_detect_responses_task = asyncio.create_task(send_detect_responses())
            
            while True:
                try:
                    detect_config = await websocket.receive_json()
                    detect_request = odrpc.DetectRequest(**detect_config)
                    executor.submit(detect_thread, detect_request)
                except TypeError:
                    await detect_responses.put(odrpc.DetectResponse(error='could not parse request body'))
                except WebSocketDisconnect:
                    send_detect_responses_task.cancel()
                    executor.shutdown()
                    break
                except Exception as e:
                    self.logger.error("Exception({0}):{1!r}".format(type(e).__name__, e.args))
                    send_detect_responses_task.cancel()
                    executor.shutdown()
                    break

        @self.api.post("/image")
        async def image(detect_request: odrpc.DetectRequest, response: Response):
            # logger.info('image request: %s', detect_request)
            if not detect_request.image:
                detect_request.image = ".jpg"
            detect_response = self.doods.detect(detect_request)
            if detect_response.error:
                return Response(status_code=status.HTTP_400_BAD_REQUEST, content=detect_response.error)
            return Response(content=detect_response.image, media_type="image/jpeg")

        # Mount the UI directory - must be last
        self.api.mount("/", StaticFiles(directory="html", html=True), name="static")
        
    def run(self):
        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_config["loggers"]["uvicorn"]["propagate"] = False # Fix a bug in logging
        uvicorn.run(self.api, host=self.config.host, port=self.config.port, log_config=log_config) 

