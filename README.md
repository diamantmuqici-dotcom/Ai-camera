# Optional Detection Models

Place a compatible, locally hosted TensorFlow.js or ONNX model here when adding real object detection.

Recommended model outputs:

- person
- car
- truck
- motorcycle
- license plate
- road sign

The current detector-worker.js is a safe bridge and returns no detections until a model is explicitly installed and loaded. The camera app does not download an object-detection model automatically.
