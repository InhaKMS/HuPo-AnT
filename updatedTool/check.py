import json

from collections import defaultdict

def print_duplicate_ids(json_data):
    id_count = defaultdict(list)
    
    for annotation in json_data['annotations']:
        id_count[annotation['id']].append(annotation['image_id'])
    
    print("중복되는 'id'를 가지는 객체 정보:")
    for ann_id, image_ids in id_count.items():
        if len(image_ids) > 1:
            print(f"Annotation ID: {ann_id}, Image IDs: {image_ids}")

def update_duplicate_ids(json_data):
    id_count = {}
    max_id = 0

    for annotation in json_data['annotations']:
        ann_id = annotation['id']
        if ann_id in id_count:
            id_count[ann_id] += 1
        else:
            id_count[ann_id] = 1
        max_id = max(max_id, ann_id)

    for annotation in json_data['annotations']:
        ann_id = annotation['id']
        if id_count[ann_id] > 1:
            max_id += 1
            annotation['id'] = max_id
            id_count[ann_id] -= 1

    return json_data

with open('crowd_data\\crowd_gt_json\\modified_gt\\modified_gt.json', 'r') as f:
    json_data = json.load(f)

# 중복된 id를 유니크한 id로 수정
updated_json_data = update_duplicate_ids(json_data)

# 중복되는 "id"를 가지는 객체 정보 출력
print_duplicate_ids(json_data)

# 수정된 json 데이터를 파일로 저장
with open('crowd_data\\crowd_gt_json\\modified_gt\\modified_gt_중복제거.json', 'w') as f:
    json.dump(updated_json_data, f, indent=4)
