from torch.utils.tensorboard import SummaryWriter
import torch
from torch.utils.data import Dataset
import pickle
from PIL import Image
import cv2

import os, random, pickle
# import matplotlib.pyplot as plt
import numpy as np

import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


def data(path, total_images=300):
    """ Generate a simple dataset (if it doesn't already exist) """
    img_size = (32,32) # image size (w,h)

    if not os.path.exists(path):
        os.makedirs(path)
        print(path + ' has been made')
        
    if not os.path.isfile(path+'dataset'):
        images = []
        answers = []
        for i in range(total_images):
            # L gives 8-bit pixels (0-255 range of white to black)
            w,h = (random.randint(img_size[0]//3, img_size[0]), random.randint(img_size[0]//3, img_size[0]))
            x,y = (random.randint(img_size[0]//3, img_size[0]), random.randint(img_size[0]//3, img_size[0]))

            xy = [(x-w//2,y-h//2), (x+w//2,y+h//2)]
            answer = np.zeros(img_size)
            answer[xy[0][0]:xy[1][0], xy[0][1]:xy[1][1]] = 1
            answers.append(answer)
            
            # L gives 8-bit pixels (0-255 range of white to black)
            out = Image.fromarray(np.uint8(answer * 255), 'L')
            
            name = path+"img"+str(i)+".png"
            out.save(name, "PNG")
            print(name)
            images.append(name)
            
        output = [images, answers]
        with open(path+'dataset', 'wb') as fp:
            pickle.dump(output, fp)
        print("made the dataset file")

class Simple01(Dataset):
    """ Simple white background, black rectangle dataset """
    
    def __init__(self, file, transform=None):
        """
        file (string): Path to the pickle that contains [img paths, output arrays]
        """
        with open (file, 'rb') as fp:
            output = pickle.load(fp)
            self.images = output[0] # images
            self.segmentations = output[1] # segmentation
        self.transform = transform
            
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, index):
            
        img = cv2.imread(self.images[index], 0)
        y_label = torch.tensor(self.segmentations[index])
        
        if self.transform is not None:
            img = self.transform(img)
            
        return (img, y_label)

def main():
    dataset = 'simple01/'
    path = 'data/'+dataset # location to store dataset
    hparams = {
        "optim":"sgd",
        "lr": 0.001,
        "momentum":0.9,
        "batch": 32,
        "shuffle":True
    }

    data(path) # make the dataset
    train_dataset = Simple01(path+'dataset')
    train_loader = torch.utils.data.DataLoader(train_dataset, pin_memory=True,
                                                batch_size=hparams['batch'], shuffle=hparams['shuffle'])
    print('Dataset : %d EA \nDataLoader : %d SET' % (len(train_dataset),len(train_loader)))


    x,y = next(iter(train_loader))
    print(f"Feature batch shape: {x.size()}")
    print(f"Labels batch shape: {y.size()}")

if __name__ == '__main__':
    main()
