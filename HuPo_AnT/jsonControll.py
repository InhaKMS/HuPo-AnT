import json
import copy
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QFileDialog

from getSegmentationArea import SegmentationArea

class CrowdPoseJson:

    before_json = {"images": [], "annotations": [],  "categories": [
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
                [
                    16,
                    14
                ],
                [
                    14,
                    12
                ],
                [
                    17,
                    15
                ],
                [
                    15,
                    13
                ],
                [
                    12,
                    13
                ],
                [
                    6,
                    12
                ],
                [
                    7,
                    13
                ],
                [
                    6,
                    7
                ],
                [
                    6,
                    8
                ],
                [
                    7,
                    9
                ],
                [
                    8,
                    10
                ],
                [
                    9,
                    11
                ]
            ]
        }
    ]}
    after_json = {"images": [], "annotations": [],  "categories": [
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
                [
                    16,
                    14
                ],
                [
                    14,
                    12
                ],
                [
                    17,
                    15
                ],
                [
                    15,
                    13
                ],
                [
                    12,
                    13
                ],
                [
                    6,
                    12
                ],
                [
                    7,
                    13
                ],
                [
                    6,
                    7
                ],
                [
                    6,
                    8
                ],
                [
                    7,
                    9
                ],
                [
                    8,
                    10
                ],
                [
                    9,
                    11
                ]
            ]
        }
    ]}

    def __init__(self, parent, imgId = 100, fileName = 'img.png'):
        self.parent = parent
    def getLastOIDnum(self) -> int:
        maxoid = 0
        for obj in self.after_json['annotations']:
            if obj["id"] > maxoid:
                maxoid = obj["id"]
        if maxoid <= 2000000:
            maxoid = 2000000
        else:
            maxoid += 1
        return maxoid
    def loadJson(self):
        fileName, _ = QFileDialog.getOpenFileName(self.parent, 'Select Files', '', 'Text files(*.json)')
        if fileName:
            file = QFile(fileName)
            if file.open(QFile.ReadOnly | QFile.Text):
                textStream = QTextStream(file)
                jsonString = textStream.readAll()
                file.close()
                try:
                    doc = json.loads(jsonString)  # JSON 문자열을 Python 객체로 변환
                    self.before_json = copy.deepcopy(doc)
                    self.after_json = copy.deepcopy(doc)
                    self.parent.lbl_tooltip.setText("Annotation file : " + fileName)
                    self.parent.setRectsbyJson()
                except json.JSONDecodeError as e:
                    self.parent.lbl_tooltip.setText(f"JSON Error: {e}")

    def setBox(self, OID, box, file_name=None):
        if OID is None:
            return -1
        image_id = int(file_name.split('.')[0])

        if isinstance(box, list) and len(box) == 4:
            box = list(map(int, box))
            found = False

            for obj in self.after_json["images"]:
                if obj["file_name"] == file_name:
                    found = True
            if not found:
                self.after_json["images"].append({
                    "file_name": file_name,
                    "id": image_id,
                    "height": self.parent.height,
                    "width": self.parent.width,
                    "crowdIndex": 0,
                    "source": "CrowdPoseTest"
                })

            found = False
            for obj in self.after_json["annotations"]:
                if obj["id"] == OID:
                    obj["bbox"] = box
                    found = True
                    break
            if not found:  # OID를 찾지 못했다면 예외 발생
                if image_id:
                    self.after_json["annotations"].append({
                            "num_keypoints": 0,
                            "iscrowd": 0,
                            "keypoints": [0] * 42,
                            "image_id": image_id,
                            "bbox": box,
                            "category_id": 1,
                            "id": OID,
                    })
                else:
                    Exception("Please put the Image ID")
        else:
            raise Exception("invalid type of bbox")

    def setKeys(self, OID: int, index, x, y, v=2):
        found = False
        for obj in self.after_json["annotations"]:
            if obj["id"] == OID:
                obj["keypoints"][index*3], obj["keypoints"][index*3+1], obj["keypoints"][index*3+2] = x, y, v
                found = True
                break
        if not found:  # OID를 찾지 못했다면 예외 발생
            pass

    def getBox(self, OID):
        for obj in self.after_json["annotations"]:
            if obj["id"] == OID:
                return obj["bbox"]
        return [0, 0, 0, 0]

    def delObj(self, OID):
        for i, obj in enumerate(self.after_json["annotations"]):
            if obj["id"] == OID:
                del self.after_json["annotations"][i]
                return 1

        return -1

    def delKey(self, OID, id):
        if id == -1:
            return
        for i, obj in enumerate(self.after_json["annotations"]):
            if obj["id"] == OID:
                self.after_json["annotations"][i]["keypoints"][id*3] = 0
                self.after_json["annotations"][i]["keypoints"][id*3+1] = 0
                self.after_json["annotations"][i]["keypoints"][id*3+2] = 0
                return 1
        return -1

    def isExistImage(self, id: int) -> bool:
        for img in self.after_json["images"]:
            if id == img["id"]:
                return True
        return False
    
    # [24.03.13 cy] 임계값을 통한 필터링 메서드 추가
    
    def filtered_by_crowd_index(self, min_value, min_inclusive, min_exclusive, max_value, max_inclusive, max_exclusive):

        # 최소/최대 조건 설정
        if min_inclusive:
            min_condition = lambda x: x >= min_value
        elif min_exclusive:
            min_condition = lambda x: x > min_value
        else:
            min_condition = lambda x: True  # 기본적으로 모든 값을 포함
        
        if max_inclusive:
            max_condition = lambda x: x <= max_value
        elif max_exclusive:
            max_condition = lambda x: x < max_value
        else:
            max_condition = lambda x: True  # 기본적으로 모든 값을 포함
        
        # 조건에 맞는 이미지 필터링
        filtered_images = [img for img in self.after_json['images'] if min_condition(img.get('crowdIndex', 0)) and max_condition(img.get('crowdIndex', 0))]
        
        # 필터링된 이미지에 맞는 어노테이션 필터링
        filtered_annotations = [ann for ann in self.after_json['annotations'] if any(img['id'] == ann['image_id'] for img in filtered_images)]
        
        # 필터링된 데이터로 json 구성
        filtered_json = {
            "images": filtered_images,
            "annotations": filtered_annotations,
            "categories": self.after_json['categories']
        }
        return filtered_json
    
    def filtered_by_keypoints(self, threshold):

        # 지정된 임계값 이상의 num_keypoints를 가진 어노테이션만 필터링
        filtered_annotations = [ann for ann in self.after_json['annotations'] if ann['num_keypoints'] >= threshold]
        
        # 필터링된 어노테이션에 해당하는 이미지 id 추출
        image_ids = {ann['image_id'] for ann in filtered_annotations}
        filtered_images = [img for img in self.after_json['images'] if img['id'] in image_ids]
        
        # 필터링된 데이터로 새로운 json 구성
        filtered_json = {
            "images": filtered_images,
            "annotations": filtered_annotations,
            "categories": self.after_json['categories']
        }
        return filtered_json
    
    # [24.03.13 cy] iscrowd=1 제거
    def remove_iscrowd(self):
        # is_crowd가 1인 어노테이션을 제거
        filtered_annotations = [ann for ann in self.after_json['annotations'] if ann.get('iscrowd', 0) == 0]
        
        # 필터링된 어노테이션에 해당하는 이미지 id 추출
        image_ids = {ann['image_id'] for ann in filtered_annotations}
        filtered_images = [img for img in self.after_json['images'] if img['id'] in image_ids]
        
        # 필터링된 데이터로 새로운 json 구성
        filtered_json = {
            "images": filtered_images,
            "annotations": filtered_annotations,
            "categories": self.after_json['categories']
        }
        
        # after_json 업데이트
        self.after_json = filtered_json
        
        return filtered_json
    
    # [24.03.28 cy] 객체 개수로 필터링
    def filtered_by_object_count(self, min_count, max_count):
        # 이미지 ID별 어노테이션 개수 계산
        annotation_count_by_image = {}
        for ann in self.after_json['annotations']:
            image_id = ann['image_id']
            annotation_count_by_image[image_id] = annotation_count_by_image.get(image_id, 0) + 1
        
        # 'x 이상 y 이하' 조건에 맞는 이미지 필터링
        filtered_images = [img for img in self.after_json['images'] if min_count <= annotation_count_by_image.get(img['id'], 0) <= max_count]
        
        # 필터링된 이미지에 해당하는 어노테이션 필터링
        filtered_annotations = [ann for ann in self.after_json['annotations'] if ann['image_id'] in {img['id'] for img in filtered_images}]
        
        # 필터링된 데이터로 새로운 json 구성
        filtered_json = {
            "images": filtered_images,
            "annotations": filtered_annotations,
            "categories": self.after_json['categories']
        }
        return filtered_json
    
    # [24.03.28 cy] 바운딩 박스 크기로 필터링
    def filtered_by_boundingbox_size(self, min_size, max_size):
        filtered_annotations = [
            ann for ann in self.after_json['annotations'] 
            if min_size <= ann['bbox'][2] * ann['bbox'][3] <= max_size
        ]
        
        image_ids = {ann['image_id'] for ann in filtered_annotations}
        filtered_images = [img for img in self.after_json['images'] if img['id'] in image_ids]
        
        filtered_json = {
            "images": filtered_images,
            "annotations": filtered_annotations,
            "categories": self.after_json['categories']
        }
        return filtered_json
    
    # [24.05.22 js] 객체들의 중복된 id를 새로운 id로 변경
    def update_duplicate_ids(self):
        id_count = {}
        max_id = 0

        for annotation in self.after_json['annotations']:
            ann_id = annotation['id']
            if ann_id in id_count:
                id_count[ann_id] += 1
            else:
                id_count[ann_id] = 1
            max_id = max(max_id, ann_id)

        for annotation in self.after_json['annotations']:
            ann_id = annotation['id']
            if id_count[ann_id] > 1:
                max_id += 1
                annotation['id'] = max_id
                id_count[ann_id] -= 1
        # 수정된 json 구성
        updated_json = {
            "images": self.after_json['images'],
            "annotations": self.after_json['annotations'],
            "categories": self.after_json['categories']
        }
        self.after_json = updated_json
        return updated_json

    # [24.11.06 js] Segmentations 정보를 추가
    def segmentation(self):
        segmentation_area = SegmentationArea()
        
        for annotation in self.after_json['annotations']:
            # 어노테이션에 필요한 필드가 있는지 확인
            if 'keypoints' in annotation and 'bbox' in annotation:
                # segmentation과 area를 계산
                segmentation, area = segmentation_area.process_annotations(annotation)
                # 필드가 없으면 생성하고 있으면 업데이트
                annotation['segmentation'] = segmentation
                annotation['area'] = area
            else:
                # 필요한 필드가 없을 경우 segmentation에 빈 배열, area에 0을 설정
                annotation['segmentation'] = []
                annotation['area'] = 0
                # 추가로 알림 메시지를 출력하거나 로그를 남길 수 있습니다.
                print(f"Annotation ID {annotation['id']}에 keypoints 또는 bbox가 없어 기본값을 설정했습니다.")
        
        # 수정된 json 구성 (필요 시)
        updated_json = {
            "images": self.after_json['images'],
            "annotations": self.after_json['annotations'],
            "categories": self.after_json['categories']
        }
        self.after_json = updated_json
        return updated_json
