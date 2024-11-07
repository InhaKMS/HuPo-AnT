import json
import os

def convert_coco_to_crowdpose(input_file, output_file):
    # Load COCO JSON file
    with open(input_file, 'r') as f:
        coco_data = json.load(f)

    # Create CrowdPose format dictionary
    crowdpose_data = {
        "images": [],
        "annotations": [],
        "categories": [
            {
                "supercategory": "person",
                "id": 1,
                "name": "person",
                "keypoints": [
                    "left_shoulder",
                    "right_shoulder",
                    "left_elbow",
                    "right_elbow",
                    "left_wrist",
                    "right_wrist",
                    "left_hip",
                    "right_hip",
                    "left_knee",
                    "right_knee",
                    "left_ankle",
                    "right_ankle",
                    "head",
                    "neck"
                ],
                "skeleton": [
                    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13], [6, 12],
                    [7, 13], [6, 7], [6, 8], [7, 9], [8, 10], [9, 11]
                ]
            }
        ]
    }

    # Map COCO image IDs to CrowdPose image IDs
    image_id_map = {}

    # Convert images
    for coco_image in coco_data["images"]:
        image_id = int(os.path.splitext(coco_image["file_name"])[0])
        image_id_map[coco_image["id"]] = image_id
        
        crowdpose_image = {
            "file_name": coco_image["file_name"],
            "id": image_id,
            "height": coco_image["height"],
            "width": coco_image["width"],
            "crowdIndex": 0
        }
        
        crowdpose_data["images"].append(crowdpose_image)

    # Convert annotations
    for coco_annotation in coco_data["annotations"]:
        if coco_annotation["num_keypoints"] == 0:
            continue
        
        keypoints = coco_annotation["keypoints"]
        
        # Map COCO keypoints to CrowdPose keypoints
        crowdpose_keypoints = [0] * (14 * 3)  # Initialize keypoints with 0s

        # Mapping: COCO index -> CrowdPose index
        keypoint_mapping = {
            5: 0,    # left_shoulder
            6: 1,    # right_shoulder
            7: 2,    # left_elbow
            8: 3,    # right_elbow
            9: 4,    # left_wrist
            10: 5,   # right_wrist
            11: 6,   # left_hip
            12: 7,   # right_hip
            13: 8,   # left_knee
            14: 9,   # right_knee
            15: 10,  # left_ankle
            16: 11   # right_ankle
        }

        for coco_index, crowdpose_index in keypoint_mapping.items():
            coco_keypoint = keypoints[coco_index * 3 : coco_index * 3 + 3]
            if coco_keypoint[2] > 0:
                crowdpose_keypoints[crowdpose_index * 3] = coco_keypoint[0]
                crowdpose_keypoints[crowdpose_index * 3 + 1] = coco_keypoint[1]
                crowdpose_keypoints[crowdpose_index * 3 + 2] = coco_keypoint[2]

        # Head keypoint (same as nose keypoint)
        if keypoints[3*0] > 0:
            crowdpose_keypoints[12 * 3] = keypoints[3*0]
            crowdpose_keypoints[12 * 3 + 1] = keypoints[3*0+1]
            crowdpose_keypoints[12 * 3 + 2] = keypoints[3*0+2]

        # Neck keypoints (average of left_shoulder and right_shoulder)
        if keypoints[3*5] > 0 and keypoints[3*6] > 0:
            # 5번째와 6번째 keypoints가 둘 다 있으면, neck의 위치와 점수를 계산합니다.
            neck_x = (keypoints[3*5] + keypoints[3*6]) / 2
            neck_y = (keypoints[3*5+1] + keypoints[3*6+1]) / 2
            neck_score = (keypoints[3*5+2] + keypoints[3*6+2]) / 2
            crowdpose_keypoints[13 * 3] = neck_x
            crowdpose_keypoints[13 * 3 + 1] = neck_y
            crowdpose_keypoints[13 * 3 + 2] = neck_score
        else:
            # 5번째 또는 6번째 keypoints 중 하나라도 없으면, neck 정보를 0으로 설정합니다.
            crowdpose_keypoints[13 * 3] = 0
            crowdpose_keypoints[13 * 3 + 1] = 0
            crowdpose_keypoints[13 * 3 + 2] = 0

        crowdpose_annotation = {
            "num_keypoints": sum(1 for i in range(2, len(crowdpose_keypoints), 3) if crowdpose_keypoints[i] > 0),
            "iscrowd": coco_annotation["iscrowd"],
            "keypoints": crowdpose_keypoints,
            "image_id": image_id_map[coco_annotation["image_id"]],
            "bbox": coco_annotation["bbox"],
            "category_id": 1,
            "id": len(crowdpose_data["annotations"]) + 1
        }
        
        crowdpose_data["annotations"].append(crowdpose_annotation)

    # Save CrowdPose JSON file
    with open(output_file, 'w') as f:
        json.dump(crowdpose_data, f, indent=4)

    print(f"Conversion completed. CrowdPose JSON file saved to: {output_file}")


# Example usage
input_file = "coco_val2017.json"
output_file = "coco_val2017_2.json"
convert_coco_to_crowdpose(input_file, output_file)
