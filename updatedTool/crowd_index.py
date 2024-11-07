import json

# Rewriting the getCrowdIndex method based on the above calculation method
def get_crowd_index(annotations):
    """
    Calculate the crowd index for a given set of annotations.
    :param annotations: List of annotations for an image.
    :return: The average crowd index of the image.
    """
    individual_crowd_indices = []

    for i, annotation_i in enumerate(annotations):
        bbox_i = annotation_i['bbox']
        keypoints_i = annotation_i['keypoints']
        own_joints_count_i = 0
        other_joints_inside_bbox_i = 0

        # Count own valid keypoints for this annotation
        for k in range(0, len(keypoints_i), 3):
            if keypoints_i[k + 2] != 0:  # valid keypoint
                own_joints_count_i += 1
        own_joints_count_i = min(own_joints_count_i, 14)  # Limiting to 14 as per the initial observation

        # Count other's keypoints inside this bbox
        for j, annotation_j in enumerate(annotations):
            if i != j:  # Looking for other's keypoints inside bbox
                keypoints_j = annotation_j.get('keypoints', [])
                for k in range(0, len(keypoints_j), 3):
                    if keypoints_j[k + 2] != 0:  # valid keypoint
                        if (bbox_i[0] <= keypoints_j[k] <= bbox_i[0] + bbox_i[2] and
                                bbox_i[1] <= keypoints_j[k + 1] <= bbox_i[1] + bbox_i[3]):
                            other_joints_inside_bbox_i += 1

        # Calculate the crowd index for this bbox if there are own joints
        if own_joints_count_i != 0:
            individual_crowd_indices.append(other_joints_inside_bbox_i / own_joints_count_i)

    # Calculate the average crowd index for the image, excluding zero denominators
    average_crowd_index = (sum(individual_crowd_indices) / len(individual_crowd_indices)
                           if individual_crowd_indices else 0)


    return round(average_crowd_index, 2)  # Rounding to 2 decimal places as per the original method

def get_crowd_ratio(annotations):
    """
    Calculate the crowd index for a given set of annotations.
    :param annotations: List of annotations for an image.
    :return: The average crowd index of the image.
    """
    individual_crowd_indices = []

    for i, annotation_i in enumerate(annotations):
        bbox_i = annotation_i['bbox']
        keypoints_i = annotation_i['keypoints']
        own_joints_count_i = 0
        other_joints_inside_bbox_i = 0

        # Count own valid keypoints for this annotation
        for k in range(0, len(keypoints_i), 3):
            if keypoints_i[k + 2] != 0:  # valid keypoint
                own_joints_count_i += 1
        own_joints_count_i = min(own_joints_count_i, 14)  # Limiting to 14 as per the initial observation

        # Count other's keypoints inside this bbox
        for j, annotation_j in enumerate(annotations):
            if i != j:  # Looking for other's keypoints inside bbox
                keypoints_j = annotation_j.get('keypoints', [])
                for k in range(0, len(keypoints_j), 3):
                    if keypoints_j[k + 2] != 0:  # valid keypoint
                        if (bbox_i[0] <= keypoints_j[k] <= bbox_i[0] + bbox_i[2] and
                                bbox_i[1] <= keypoints_j[k + 1] <= bbox_i[1] + bbox_i[3]):
                            other_joints_inside_bbox_i += 1

        # Calculate the crowd index for this bbox if there are own joints
        if own_joints_count_i != 0:

            individual_crowd_indices.append((annotation_i["id"], round(other_joints_inside_bbox_i / own_joints_count_i, 2)))


    return individual_crowd_indices # Rounding to 2 decimal places as per the original method

# Function to calculate Crowd Index for each image in the dataset and compare with original values
def verify_crowd_index_on_dataset(data):
    # Extracting image IDs and corresponding annotations
    images = data['images']
    annotations = data['annotations']

    # Grouping annotations by image ID
    annotations_by_image = {}
    for annotation in annotations:
        image_id = annotation['image_id']
        if image_id not in annotations_by_image:
            annotations_by_image[image_id] = []
        annotations_by_image[image_id].append(annotation)

    # Calculating and comparing Crowd Index values
    discrepancies = []
    for image in images:
        image_id = image['id']
        crowd_index_original = image.get('crowdIndex', None)  # Some images may not have this field
        annotations_for_image = annotations_by_image.get(image_id, [])
        crowd_index_calculated = get_crowd_index(annotations_for_image)

        # Check for discrepancies
        #if crowd_index_original is not None and round(crowd_index_calculated, 2) != round(crowd_index_original, 2):
        if True:
            discrepancies.append({
                'image_id': image_id,
                # 'crowd_index_original': crowd_index_original,
                'crowdIndex': crowd_index_calculated
            })

    return discrepancies

if __name__ == '__main__':
    # Verify the Crowd Index on the entire dataset
    with open(r'with_new_keypoints_crowdpose.json', 'r') as file:
        data = json.load(file)
        discrepancies = verify_crowd_index_on_dataset(data)

    with open(r'updated_withcrowdindex_crowdpose.json', 'w') as file2:
        json.dump(discrepancies, file2, indent=2)
