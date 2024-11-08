import numpy as np
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union

class SegmentationArea:
    def get_keypoints_dict(self, keypoints):
        return {
            'left_shoulder': (keypoints[0], keypoints[1], keypoints[2]),
            'right_shoulder': (keypoints[3], keypoints[4], keypoints[5]),
            'left_elbow': (keypoints[6], keypoints[7], keypoints[8]),
            'right_elbow': (keypoints[9], keypoints[10], keypoints[11]),
            'left_wrist': (keypoints[12], keypoints[13], keypoints[14]),
            'right_wrist': (keypoints[15], keypoints[16], keypoints[17]),
            'left_hip': (keypoints[18], keypoints[19], keypoints[20]),
            'right_hip': (keypoints[21], keypoints[22], keypoints[23]),
            'left_knee': (keypoints[24], keypoints[25], keypoints[26]),
            'right_knee': (keypoints[27], keypoints[28], keypoints[29]),
            'left_ankle': (keypoints[30], keypoints[31], keypoints[32]),
            'right_ankle': (keypoints[33], keypoints[34], keypoints[35]),
            'head': (keypoints[36], keypoints[37], keypoints[38]),
            'neck': (keypoints[39], keypoints[40], keypoints[41])
        }

    def euclidean_distance(self, p1, p2):
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def get_valid_keypoints(self, kps_dict):
        return {k: (v[0], v[1]) for k, v in kps_dict.items() if v[2] > 0}

    def get_offset_point(self, x1, y1, x2, y2, width):
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            return [None, None, None, None]
        dx /= length
        dy /= length
        px = -dy
        py = dx
        offset1 = (x1 + px * width / 2, y1 + py * width / 2)
        offset2 = (x1 - px * width / 2, y1 - py * width / 2)
        offset4 = (x2 + px * width / 2, y2 + py * width / 2)
        offset3 = (x2 - px * width / 2, y2 - py * width / 2)
        return [offset1, offset2, offset3, offset4]

    # 다각형 생성 함수
    def add_polygon_if_valid(self, points, polygons):
        if all(points):
            polygon = Polygon(points)
            if polygon.is_valid and polygon.area > 0:
                polygons.append(polygon)

    def safe_euclidean_distance(self, p1, p2):
        if p1 is None or p2 is None:
            return 0
        return self.euclidean_distance(p1, p2)

    def reorder_keypoints(self, kp1, kp2):
        return kp2, kp1

    def clip_polygon_to_bbox(self, polygon, bbox):
        min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]
        bbox_polygon = Polygon([(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)])
        return polygon.intersection(bbox_polygon)

    def process_annotations(self, annotation):
        keypoints = annotation['keypoints']
        bbox = annotation['bbox']
        keypoints_dict = self.get_keypoints_dict(keypoints)
        valid_keypoints = self.get_valid_keypoints(keypoints_dict)
    
        # 어깨를 기준으로 몸이 뒤집힌 상태 파악
        is_flipped = False
        if valid_keypoints.get('left_shoulder') and valid_keypoints.get('right_shoulder'):
            if valid_keypoints['left_shoulder'][0] < valid_keypoints['right_shoulder'][0]:
                is_flipped = True
                valid_keypoints['left_shoulder'], valid_keypoints['right_shoulder'] = self.reorder_keypoints(valid_keypoints['left_shoulder'], valid_keypoints['right_shoulder'])

        # 나머지 키포인트 재정렬
        if is_flipped:
            keypoint_pairs = [
                ('left_elbow', 'right_elbow'),
                ('left_wrist', 'right_wrist'),
                ('left_hip', 'right_hip'),
                ('left_knee', 'right_knee'),
                ('left_ankle', 'right_ankle')
            ]
            
            for left_key, right_key in keypoint_pairs:
                if valid_keypoints.get(left_key) and valid_keypoints.get(right_key):
                    valid_keypoints[left_key], valid_keypoints[right_key] = self.reorder_keypoints(valid_keypoints[left_key], valid_keypoints[right_key])
                elif valid_keypoints.get(left_key) and not valid_keypoints.get(right_key):
                    valid_keypoints[right_key] = valid_keypoints.pop(left_key)
                elif valid_keypoints.get(right_key) and not valid_keypoints.get(left_key):
                    valid_keypoints[left_key] = valid_keypoints.pop(right_key)

        shoulder_width = self.safe_euclidean_distance(valid_keypoints.get('left_shoulder'), valid_keypoints.get('right_shoulder'))
        left_upper_arm_width = 0.25 * self.safe_euclidean_distance(valid_keypoints.get('left_shoulder'), valid_keypoints.get('left_elbow'))
        right_upper_arm_width = 0.25 * self.safe_euclidean_distance(valid_keypoints.get('right_shoulder'), valid_keypoints.get('right_elbow'))
        left_thigh_width = 0.45 * self.safe_euclidean_distance(valid_keypoints.get('left_hip'), valid_keypoints.get('left_knee'))
        right_thigh_width = 0.45 * self.safe_euclidean_distance(valid_keypoints.get('right_hip'), valid_keypoints.get('right_knee'))
        left_calf_width = 0.4 * self.safe_euclidean_distance(valid_keypoints.get('left_knee'), valid_keypoints.get('left_ankle'))
        right_calf_width = 0.4 * self.safe_euclidean_distance(valid_keypoints.get('right_knee'), valid_keypoints.get('right_ankle'))

        polygons = []

        # 각 신체 부위별 폴리곤 생성
        if 'left_shoulder' in valid_keypoints and 'left_elbow' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['left_shoulder'][0], valid_keypoints['left_shoulder'][1], valid_keypoints['left_elbow'][0], valid_keypoints['left_elbow'][1], left_upper_arm_width)
            self.add_polygon_if_valid(points, polygons)

        if 'right_shoulder' in valid_keypoints and 'right_elbow' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['right_shoulder'][0], valid_keypoints['right_shoulder'][1], valid_keypoints['right_elbow'][0], valid_keypoints['right_elbow'][1], right_upper_arm_width)
            self.add_polygon_if_valid(points, polygons)

        if 'left_elbow' in valid_keypoints and 'left_wrist' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['left_elbow'][0], valid_keypoints['left_elbow'][1], valid_keypoints['left_wrist'][0], valid_keypoints['left_wrist'][1], left_upper_arm_width)
            self.add_polygon_if_valid(points, polygons)

        if 'right_elbow' in valid_keypoints and 'right_wrist' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['right_elbow'][0], valid_keypoints['right_elbow'][1], valid_keypoints['right_wrist'][0], valid_keypoints['right_wrist'][1], right_upper_arm_width)
            self.add_polygon_if_valid(points, polygons)

        if 'left_hip' in valid_keypoints and 'right_hip' in valid_keypoints and 'left_shoulder' in valid_keypoints and 'right_shoulder' in valid_keypoints:
            points = [
                (valid_keypoints['left_shoulder'][0], valid_keypoints['left_shoulder'][1]),
                (valid_keypoints['right_shoulder'][0], valid_keypoints['right_shoulder'][1]),
                (valid_keypoints['right_hip'][0] - right_thigh_width / 2, valid_keypoints['right_hip'][1]),
                (valid_keypoints['left_hip'][0] + left_thigh_width / 2, valid_keypoints['left_hip'][1])
            ]
            self.add_polygon_if_valid(points, polygons)

        if 'head' in valid_keypoints and 'neck' in valid_keypoints:
            head_width = 0.6 * shoulder_width
            dx = valid_keypoints['head'][0] - valid_keypoints['neck'][0]
            dy = valid_keypoints['head'][1] - valid_keypoints['neck'][1]
            points = self.get_offset_point(valid_keypoints['head'][0] + dx, valid_keypoints['head'][1] + dy, valid_keypoints['neck'][0], valid_keypoints['neck'][1], head_width)
            self.add_polygon_if_valid(points, polygons)

        if 'neck' in valid_keypoints and 'right_shoulder' in valid_keypoints and 'left_shoulder' in valid_keypoints:
            head_width = 0.6 * shoulder_width
            points = [
                (valid_keypoints['left_shoulder'][0] + left_upper_arm_width / 2, valid_keypoints['left_shoulder'][1]),
                (valid_keypoints['right_shoulder'][0] - right_upper_arm_width / 2, valid_keypoints['right_shoulder'][1]),
                (valid_keypoints['neck'][0] - head_width / 2, valid_keypoints['neck'][1]),
                (valid_keypoints['neck'][0] + head_width / 2, valid_keypoints['neck'][1])
            ]
            self.add_polygon_if_valid(points, polygons)

        if 'left_hip' in valid_keypoints and 'left_knee' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['left_hip'][0], valid_keypoints['left_hip'][1], valid_keypoints['left_knee'][0], valid_keypoints['left_knee'][1], left_thigh_width)
            self.add_polygon_if_valid(points, polygons)

        if 'right_hip' in valid_keypoints and 'right_knee' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['right_hip'][0], valid_keypoints['right_hip'][1], valid_keypoints['right_knee'][0], valid_keypoints['right_knee'][1], right_thigh_width)
            self.add_polygon_if_valid(points, polygons)

        if 'left_knee' in valid_keypoints and 'left_ankle' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['left_knee'][0], valid_keypoints['left_knee'][1], valid_keypoints['left_ankle'][0], valid_keypoints['left_ankle'][1], left_calf_width)
            self.add_polygon_if_valid(points, polygons)

        if 'right_knee' in valid_keypoints and 'right_ankle' in valid_keypoints:
            points = self.get_offset_point(valid_keypoints['right_knee'][0], valid_keypoints['right_knee'][1], valid_keypoints['right_ankle'][0], valid_keypoints['right_ankle'][1], right_calf_width)
            self.add_polygon_if_valid(points, polygons)

        # 유효한 폴리곤 병합
        polygons = [polygon.buffer(0) for polygon in polygons]
        body_polygon = unary_union(polygons)

        # 바운딩 박스로 폴리곤 클리핑
        body_polygon = self.clip_polygon_to_bbox(body_polygon, bbox)

        # 세그먼트 좌표와 영역 계산
        segmentation = []
        area = 0

        if body_polygon.is_empty:
            return segmentation, area

        if body_polygon.geom_type == 'Polygon':
            coords = np.array(body_polygon.exterior.coords).ravel().tolist()
            segmentation.append(coords)
            area = body_polygon.area
        elif body_polygon.geom_type == 'MultiPolygon':
            for poly in body_polygon.geoms:
                coords = np.array(poly.exterior.coords).ravel().tolist()
                segmentation.append(coords)
                area += poly.area

        return segmentation, area
