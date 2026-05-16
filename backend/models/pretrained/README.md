Pretrained model assets
======================

Accident CNN model options
--------------------------
1) Optional custom Keras model:
   - accident_cnn.keras

2) Automatic fallback chain:
   - MobileNetV2 feature CNN (TensorFlow)
   - SqueezeNet ONNX fallback (squeezenet1.1-7.onnx)

Vehicle object detection upgrade
-------------------------------
The traffic analyzer now uses a pretrained MobileNet-SSD object detector first.
Model files are auto-downloaded on first run:
- mobilenet_ssd_deploy.prototxt
- mobilenet_ssd.caffemodel

If download or loading fails, the system falls back to contour-based vehicle detection.
