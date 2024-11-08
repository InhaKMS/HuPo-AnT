# HuPo AnT : INHA KMS HumanPose Annotation Tool

<p align='center'>
    <img src="https://github.com/user-attachments/assets/ce6b2e64-529d-41b7-8d80-ff23170534ca" alt="그림1">
</p>



## Introduction
INHA KMS's HuPo AnT is a tool designed for generating and verifying ground truth (GT) data by annotating key points for human pose recognition in crowd scenarios. <br>
It adheres to the CrowdPose dataset format, supporting multiple annotators to work on the same input video simultaneously. <br>
This tool enables the creation of filtered datasets for various research purposes.


### Capabilities

- Load and visualize a Crowd style dataset
- Add/Delete/Edit Bounding Boxes
- Add/Delete/Edit Keypoints
- Remove iscrowd box
- Calculate crowdindex
- Save images with applied filtering (keypoints, crowdindex, objects, boxsize)
- Heuristic segmentation


## Environmnet
```
Python 3.8.10
numpy==1.24.4
Pillow==10.2.0
PyQt5==5.15.10
Shapely==2.0.5
```

## Usage
Clone the repo:  
```$ git clone https://github.com/InhaKMS/HuPo-AnT```

 - Window
   [Annotation Tool for Window](https://drive.google.com/file/d/1BcSmCznT5tKi8IChe9eAQczTs-E7fNxp/view?usp=share_link) (Google Drive)
   1. Unzip the 'Annotation Tool for Window' folder  
   2. Run by clicking the main.exe file  
   
 - MacOS & Linux  
    Execute the following commands in the terminal
    ```
    $ cd updatedTool
    $ python3 main.py
    ```

Please refer to the manual below for detailed instructions on using the Annotation Tool.


## Dataset

[Test image](https://drive.google.com/file/d/1aDGcgTgcxS7itMkxBy4rjfeahAdm6fEn/view?usp=sharing) (Google Drive)

[Annotations](https://drive.google.com/drive/folders/1TP_8ypQGAc0ab8MIWglJBqplhscvccUY?usp=share_link) (Google Drive)



## Contributors

