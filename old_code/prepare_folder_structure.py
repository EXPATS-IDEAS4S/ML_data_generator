# %%
import numpy as np
import glob
import random
import os
import shutil

# %%
# some helper methods to read timestamps and copy files
def get_datetime_str_from_imagefile(imagefile):
    return os.path.basename(imagefile)[:13]

def sort_images_into_folder(image_list, out_path):
    for img in image_list:
        out_img = os.path.join(out_path, os.path.basename(img))
        # if img dows not yet exists in new location
        if not os.path.exists(out_img):
            shutil.copyfile(img, out_img)

# %%
# method for sorting images into training and testing folder etc.
def sort_image_pairs_into_train_val(data_path, out_path, train_ratio=0.9):

    # read in all IR images
    IR_files = sorted(glob.glob(f"{data_path}/IR_108/*.png"))

    # random select train and val images
    random.shuffle(IR_files)
    split_idx = int(train_ratio*len(IR_files))
    train_IR_files = IR_files[:split_idx]
    val_IR_files = IR_files[split_idx:]

    # get corresponding VIS images for training dataset
    train_VIS_files = []
    for ir_train in train_IR_files:
        vis_train = ir_train.replace("IR_108", "VIS006")
        if not os.path.exists(vis_train):
            print("There is no corresponding visible image for the IR image: ", ir_train)
        else:
            train_VIS_files.append(vis_train)

    # get corresponding VIS images for validation dataset
    val_VIS_files = []
    for ir_val in val_IR_files:
        vis_val = ir_val.replace("IR_108", "VIS006")
        if not os.path.exists(vis_val):
            print("There is no corresponding visible image for the IR image: ", ir_val)
        else:
            val_VIS_files.append(vis_val)
    
    # sort the training data into new train folder
    train_images = train_IR_files + train_VIS_files
    train_path = os.path.join(out_path, "train")
    if not os.path.exists(train_path):
        os.makedirs(train_path)
    sort_images_into_folder(train_images, train_path)

    # sort the valdiation data into new val folder
    val_images = val_IR_files + val_VIS_files
    val_path = os.path.join(out_path, "val")
    if not os.path.exists(val_path):
        os.makedirs(val_path)
    sort_images_into_folder(val_images, val_path)

# %%
if __name__ == "__main__":
    # path to project directory
    PROJECT_DIR = "/net/merisi/pbigalke/teaching/METFUT2024/CGAN_Pix2Pix_MSG"
    data_path = f"{PROJECT_DIR}/test_data"
    out_path = f"{PROJECT_DIR}/VIS_IR_images"

    sort_image_pairs_into_train_val(data_path, out_path)
# %%
