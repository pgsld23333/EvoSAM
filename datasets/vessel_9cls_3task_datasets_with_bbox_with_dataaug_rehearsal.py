import json
import os
import numpy as np
import cv2
import torch

from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image
from .data_aug import pad_image, expand_bbox, direction_augmentation, random_crop


orders = [
    {0:0, 1:1, 2:2}, 
    {0:0, 1:2, 2:1},
    {0:1, 1:0, 2:2},
    {0:1, 1:2, 2:0},
    {0:2, 1:0, 2:1},
    {0:2, 1:1, 2:0}
]

class VesselSeqDatasetInference(Dataset):
    def __init__(self, data_root, order_idx):
        self.data_root = data_root
        self.data_list = None
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
        self.color_jittor = transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["train"]

    def __len__(self):
        return len(self.data_list)
    
    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask
    
    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        bbox = expand_bbox(bbox, W, W, rand_val=100)
        # img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        # img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        # img = self.color_jittor(Image.fromarray(img))
        # img = np.array(img)
        assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)
        mask = cv2.resize(mask, (ts, ts))
        mask[mask < 0.1] = 0
        mask[mask != 0] = 1
        
        
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img, 
            label
        )


class VesselSeqDatasetInferenceWithAug(Dataset):
    def __init__(self, data_root, order_idx):
        self.data_root = data_root
        self.data_list = None
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            # transforms.RandomHorizontalFlip(p=0.5),
            # transforms.RandomVerticalFlip(p=0.5),
            # transforms.RandomApply([transforms.RandomRotation((90, 90))], p=0.5),
            # transforms.RandomApply([transforms.RandomRotation((270, 270))], p=0.5),
            # transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
        self.color_jittor = transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["train"]

    def __len__(self):
        return len(self.data_list)
    
    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask
    
    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        H, W = img.shape[0], img.shape[1]
        # mask = self.get_mask(points, W, H)
        # img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        bbox = expand_bbox(bbox, H, W, rand_val=100)
        # img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        # W_ = img.shape[0]
        # img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        # img = self.color_jittor(Image.fromarray(img))
        # img = np.array(img)
        # assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = cv2.cvtColor(bbox_cropped_img, cv2.COLOR_BGR2RGB)
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        # ts = self.target_size
        # img = cv2.resize(img, (ts, ts))
        # bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        # mask = (mask == 255).astype(np.uint8)
        # mask = cv2.resize(mask, (ts, ts))
        # mask[mask < 0.1] = 0
        # mask[mask != 0] = 1
        
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # import pdb; pdb.set_trace()
        # bimg = (bbox_cropped_img - bbox_cropped_img.min()) / (bbox_cropped_img.max() - bbox_cropped_img.min())
        # bimg = bimg.permute(1, 2, 0).numpy() * 255
        # bimg = bimg.astype(np.uint8)
        # bimg = cv2.cvtColor(bimg, cv2.COLOR_RGB2BGR)
        # cv2.imwrite("img_vis2.jpg", bimg)
        # cv2.imwrite("img_vis.png", img_vis)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        # img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            0, 0, 0,
            os.path.basename(img_path), 
            bbox_cropped_img, 
            label
        )


class VesselTestDatasetWithLabel(Dataset):
    def __init__(self, data_root, order_idx):
        self.data_root = data_root
        self.data_list = []
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["test"]

    def __len__(self):
        return len(self.data_list)

    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask

    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        # bbox = expand_bbox(bbox, W, W, rand_val=100)
        # img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        # img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        # img = self.color_jittor(Image.fromarray(img))
        # img = np.array(img)
        # assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)

        # mask = cv2.resize(mask, (ts, ts))
        # mask[mask < 0.1] = 0
        # mask[mask != 0] = 1
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img, 
            label
        )






class VesselSeqDatasetTest(Dataset):
    def __init__(self, data_root, order_idx):
        self.data_root = data_root
        self.data_list = None
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
        self.color_jittor = transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["train"]

    def __len__(self):
        return len(self.data_list)
    
    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask
    
    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        bbox = expand_bbox(bbox, W, W, rand_val=100)
        # img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        # img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        # img = self.color_jittor(Image.fromarray(img))
        # img = np.array(img)
        assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)
        mask = cv2.resize(mask, (ts, ts))
        mask[mask < 0.1] = 0
        mask[mask != 0] = 1
        
        
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img
        )



class VesselSeqDataset(Dataset):
    def __init__(self, data_root, order_idx, rehearsal_rate):
        self.data_root = data_root
        self.data_list = None
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
        self.color_jittor = transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
        self.rehearal_rate = rehearsal_rate 
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["train"]
        
        if task_id > 0:
            for i in range(task_id):
                i_ = orders[self.order_idx][i]
                with open(os.path.join(self.data_root, f"task{i_+1}_list_test_expand_only_shuffle.json"), 'r') as f:
                    train_list = json.load(f)["train"]
                    print("task{}/{} rehearsal: {} * {} = {}".format(i,i_, len(train_list), self.rehearal_rate, int(len(train_list) * self.rehearal_rate)))
                    self.data_list = self.data_list + train_list[:int(len(train_list) * self.rehearal_rate)]

    def __len__(self):
        return len(self.data_list)
    
    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask
    
    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        bbox = expand_bbox(bbox, W, W, rand_val=100)
        img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        img = self.color_jittor(Image.fromarray(img))
        img = np.array(img)
        assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)
        mask = cv2.resize(mask, (ts, ts))
        mask[mask < 0.1] = 0
        mask[mask != 0] = 1
        
        
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img
        )
        
class VesselJointDataset(Dataset):
    def __init__(self, data_root, order_idx=None):
        self.data_root = data_root
        self.data_list = []
        for task_id in range(3):
            with open(os.path.join(self.data_root, f"task{task_id+1}_list_test_expand_only.json"), 'r') as f:
                self.data_list += json.load(f)["train"]
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
        self.color_jittor = transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
    def __len__(self):
        return len(self.data_list)

    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask

    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        bbox = expand_bbox(bbox, W, W, rand_val=100)
        img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        img = self.color_jittor(Image.fromarray(img))
        img = np.array(img)
        assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)
        mask = cv2.resize(mask, (ts, ts))
        mask[mask < 0.1] = 0
        mask[mask != 0] = 1
        
        
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img
        )

class VesselTestDataset(Dataset):
    def __init__(self, data_root, order_idx):
        self.data_root = data_root
        self.data_list = []
        self.order_idx = order_idx
        self.croped_transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(), 
            transforms.Normalize(mean=[0.48145466, 0.4578275, 0.40821073], 
                                 std=[0.26862954, 0.26130258, 0.27577711])
        ])
        self.target_size = 1024
    def load_dataset(self, task_id):
        idx = orders[self.order_idx][task_id]
        with open(os.path.join(self.data_root, f"task{idx+1}_list_test_expand_only.json"), 'r') as f:
            self.data_list = json.load(f)["test"]

    def __len__(self):
        return len(self.data_list)

    def get_mask(self, poly, W, H):
        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillPoly(mask, [np.array(poly)], 255)
        return mask

    def __getitem__(self, index):
        item = self.data_list[index]
        label, bbox, points, img_path = item["label"], item["bbox"], item["points"], item["img_path"]
        # img_path, mask_path, mask_val, bbox = self.data_list[index]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W = img.shape[0], img.shape[1]
        mask = self.get_mask(points, W, H)
        img, mask, bbox = pad_image(img, mask, bbox)

        ######################### data augmentation ##########################
        # bbox = expand_bbox(bbox, W, W, rand_val=100)
        # img, mask, bbox = random_crop(img, mask, bbox, scale=(0.1, 1.0))
        W_ = img.shape[0]
        # img, mask, bbox = direction_augmentation(img, mask, bbox, W_, W_)
        # img = self.color_jittor(Image.fromarray(img))
        # img = np.array(img)
        # assert bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= W_ and bbox[3] <= W_, f"bbox: {bbox}, W_: {W_}"
        ######################### get box-cropped image ##########################
        bbox_cropped_img = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :].copy()
        bbox_cropped_img = pad_image(bbox_cropped_img)[0]
        bbox_cropped_img = Image.fromarray(bbox_cropped_img)
        bbox_cropped_img = self.croped_transform(bbox_cropped_img)
        ##########################################################################

        ts = self.target_size
        img = cv2.resize(img, (ts, ts))
        bbox = np.array([int(bbox[0] / W_ * ts), int(bbox[1] / W_ * ts), int(bbox[2] / W_ * ts), int(bbox[3] / W_ * ts)])
        
        mask = (mask == 255).astype(np.uint8)

        # mask = cv2.resize(mask, (ts, ts))
        # mask[mask < 0.1] = 0
        # mask[mask != 0] = 1
        # img_vis = img.copy()
        # img_vis = cv2.rectangle(img_vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        # img_vis[mask.astype(bool), 0] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 0] * 0.8)
        # img_vis[mask.astype(bool), 1] = np.uint8(255 * 0.2 + img_vis[mask.astype(bool), 1] * 0.8)
        # img_vis[mask.astype(bool), 2] = np.uint8(0 * 0.2 + img_vis[mask.astype(bool), 2] * 0.8)
        # img_vis = img_vis[:, :, ::-1]
        # cv2.imwrite("test.jpg", img_vis)
        # import pdb; pdb.set_trace()

        img = (img - img.min()) / np.clip(img.max() - img.min(), a_min=1e-8, a_max=None)  # normalize to [0, 1], (H, W, 3)

        return (
            torch.tensor(img).float().permute(2, 0, 1),
            torch.tensor(mask[None, :, :]).long(),
            torch.tensor(bbox).float(),
            os.path.basename(img_path), 
            bbox_cropped_img
        )
