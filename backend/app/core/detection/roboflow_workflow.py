from inference import InferencePipeline
import cv2
from app.config import settings

def run_roboflow_workflow(video_reference=0, max_fps=30):
    def my_sink(result, video_frame):
        if result.get("output_image"):
            cv2.imshow("Workflow Image", result["output_image"].numpy_image)
            cv2.waitKey(1)
        print(result)

    pipeline = InferencePipeline.init_with_workflow(
        api_key=settings.ROBOFLOW_API_KEY,
        workspace_name=settings.ROBOFLOW_WORKSPACE,
        workflow_id=settings.ROBOFLOW_WORKFLOW_ID,
        video_reference=video_reference,
        max_fps=max_fps,
        on_prediction=my_sink
    )
    pipeline.start()
    pipeline.join()
