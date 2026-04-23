from ultralytics import YOLO

#模型				参数量	速度	精度	推荐场景
#yolov8n(Nano)		3.2M	最快	基础	手机App、树莓派
#yolov8s(Small)		11.2M	快		良好	推荐：平衡之选
#yolov8m(Medium)	25.9M	中等	更好	服务器端
#yolov8l(Large)		43.7M	慢		好		追求极致精度
#yolov8x(X-Large)	68.2M	最慢	最好	离线批量处理

# 加载YOLOv8官方预训练模型（自动下载）
model = YOLO("yolo26n.pt")  # 或 yolov8s.pt / yolov8m.pt

# 检测图片
results = model("bike.jpg")

# ========== 打印所有返回数据 ==========

# 1. 打印 results 的基本信息
print("=" * 50)
print("【Results 对象基本信息】")
print(f"results 类型: {type(results)}")
print(f"results 长度: {len(results)}")
print(f"results 内容: {results}")
print()

# 2. 遍历每个检测结果（通常只有一张图，所以 results[0] 是第一张图的结果）
for i, result in enumerate(results):
    print(f"=" * 50)
    print(f"【第 {i} 张图片的检测结果】")
    print(f"result 类型: {type(result)}")
    print()
    
    # 3. 打印 result 的所有可用属性
    print("【result 的所有可用属性】")
    for attr in dir(result):
        if not attr.startswith('_'):  # 过滤掉私有属性
            print(f"  - {attr}")
    print()
    
    # 4. 打印原始结果
    print("【result 原始内容】")
    print(result)
    print()
    
    # 5. 打印 boxes 信息（最核心）
    if result.boxes is not None:
        print("【Boxes 信息】")
        print(f"boxes 类型: {type(result.boxes)}")
        print(f"boxes 原始内容: {result.boxes}")
        print()
        
        # 6. 打印每个检测框的详细数据
        boxes = result.boxes
        print(f"检测到 {len(boxes)} 个目标")
        print()
        
        for j, box in enumerate(boxes):
            print(f"  --- 目标 {j+1} ---")
            
            # 获取所有可用数据
            # 坐标 (xyxy 格式: 左上角x, 左上角y, 右下角x, 右下角y)
            xyxy = box.xyxy[0].tolist()
            print(f"    xyxy 坐标: {xyxy}")
            
            # 坐标 (xywh 格式: 中心点x, 中心点y, 宽度, 高度)
            xywh = box.xywh[0].tolist()
            print(f"    xywh 坐标: {xywh}")
            
            # 坐标 (xyxyn 格式: 归一化后的xyxy)
            xyxyn = box.xyxyn[0].tolist()
            print(f"    xyxyn 坐标(归一化): {xyxyn}")
            
            # 坐标 (xywhn 格式: 归一化后的xywh)
            xywhn = box.xywhn[0].tolist()
            print(f"    xywhn 坐标(归一化): {xywhn}")
            
            # 置信度
            conf = box.conf[0].item()
            print(f"    置信度: {conf}")
            
            # 类别ID
            cls = int(box.cls[0].item())
            print(f"    类别ID: {cls}")
            
            # 类别名称
            cls_name = result.names[cls]
            print(f"    类别名称: {cls_name}")
            
            # 框的ID（如果有多目标跟踪时才有）
            if hasattr(box, 'id') and box.id is not None:
                obj_id = box.id[0].item()
                print(f"    目标ID: {obj_id}")
            
            print()
    else:
        print("【Boxes 信息】")
        print("未检测到任何目标（result.boxes 为 None）")
        print()
    
    # 7. 打印 masks 信息（如果有分割结果）
    if result.masks is not None:
        print("【Masks 信息】")
        print(f"masks 类型: {type(result.masks)}")
        print(f"masks 数据: {result.masks}")
        print()
    
    # 8. 打印 keypoints 信息（如果有关键点）
    if result.keypoints is not None:
        print("【Keypoints 信息】")
        print(f"keypoints 类型: {type(result.keypoints)}")
        print(f"keypoints 数据: {result.keypoints}")
        print()
    
    # 9. 打印 probs 信息（如果是分类任务）
    if result.probs is not None:
        print("【Probs 信息】")
        print(f"probs 类型: {type(result.probs)}")
        print(f"probs 数据: {result.probs}")
        print()
    
    # 10. 打印 speed 信息（推理速度）
    print("【Speed 信息】")
    print(f"预处理时间: {result.speed['preprocess']:.2f} ms")
    print(f"推理时间: {result.speed['inference']:.2f} ms")
    print(f"后处理时间: {result.speed['postprocess']:.2f} ms")
    print()
    
    # 11. 打印原图信息
    print("【原图信息】")
    print(f"原图形状: {result.orig_shape}")
    print(f"原图路径: {result.path}")
    print()

print("=" * 50)