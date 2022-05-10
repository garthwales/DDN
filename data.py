import os, random, pickle
from torch.utils.data import Dataset
import torch
import numpy as np
from PIL import Image
import cv2

from torchvision import transforms
from torch.utils.data import random_split

from nc import manual_weight

import argparse

def get_dataset(args):
    train_dataset = SimpleDatasets(args, transform=transforms.ToTensor()) #path/dataset is a pickle containing (image paths, targets)

    print(f'Total dataset size {len(train_dataset)}')
    # Training and Validation dataset
    n_val = int(len(train_dataset) * args.val)
    n_train = len(train_dataset) - n_val

    train_set, val_set = random_split(train_dataset, [n_train, n_val], generator=torch.Generator().manual_seed(0)) # Consistent splits for everything
    train_loader = torch.utils.data.DataLoader(train_set, pin_memory=True,
                                                batch_size=args.batch_size, shuffle=args.shuffle)
    val_loader = torch.utils.data.DataLoader(val_set, pin_memory=True,
                                                batch_size=args.batch_size, shuffle=args.shuffle)

    return train_loader, val_loader

def get_weights_vars(args):
    r=1
    min=False   
    if 'weights' in args.dataset:
        # If weights, check if a r value is provided
        if len(args.dataset) > len('weights'):
            diff = len('weights')-len(args.dataset)
            r = int(args.dataset[diff:])
    elif 'minW' in args.dataset:    
        min = True
        if len(args.dataset) > len('minW'):
            diff = len('minW')-len(args.dataset)
            r = int(args.dataset[diff:])
    return r, min

def data(path, args, img_size=(32,32)):
    """ Generate a simple dataset (if it doesn't already exist) 
    path - example 'data/simple01/'
    total_images - total number of images to create for the dataset
    image size - (w,h)
    """

    if not os.path.exists(path):
        os.makedirs(path)
        print(path + ' has been made')
        
    if not os.path.isfile(path+'dataset'):
        images = []
        answers = []
        for i in range(args.total_images):
            # L gives 8-bit pixels (0-255 range of white to black)
            w,h = (random.randint(img_size[0]//3, img_size[0]), random.randint(img_size[0]//3, img_size[0]))
            x,y = (random.randint(img_size[0]//3, img_size[0]), random.randint(img_size[0]//3, img_size[0]))

            xy = [(x-w//2,y-h//2), (x+w//2,y+h//2)]
            answer = np.zeros(img_size)
            answer[xy[0][0]:xy[1][0], xy[0][1]:xy[1][1]] = 1

            # L gives 8-bit pixels (0-255 range of white to black)
            out = Image.fromarray(np.uint8(answer * 255), 'L')

            name = path+"img"+str(i)+".png"
            out.save(name, "PNG")
            images.append(name)
            
            if 'simple01' == args.dataset:
                answers.append(answer)
            else:
                r, min = get_weights_vars(args)
                answers.append(manual_weight(name, r=r, minVer=min))
            
        output = [images, answers]
        with open(path+'dataset', 'wb') as fp:
            pickle.dump(output, fp)
        print("made the dataset file")

class SimpleDatasets(Dataset):
    """ Simple white background, black rectangle dataset """
    
    def __init__(self, args, transform=None):
        """
        file (string): Path to the pickle that contains [img paths, output arrays]
        """
        # append = '../../' if args.production else ''
        append = ''
        path = append + 'data/' + args.dataset + '/' + str(args.total_images) + '/' # location to store dataset
        data(path, args) # make the dataset

        with open (path+'dataset', 'rb') as fp:
            output = pickle.load(fp)
            self.images = output[0] # images
            self.segmentations = output[1] # segmentation
        self.transform = transform
            
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, index):
        img = cv2.imread(self.images[index], 0)
        # or switch to PIL.Image.open() and then img.load()?
        y_label = self.segmentations[index]
        
        if self.transform is not None:
            img = self.transform(img)
            y_label = self.transform(y_label)
            
        return (img, y_label)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='debugging arguments')
    parser.add_argument('--dataset', type=str, default='minW1', help='dataset to use: weights(r_val), simple01, minW(r_val) e.g. minW3')
    parser.add_argument('--total-images', '-ti', metavar='N', type=int, default=10, dest='total_images', help='total number of images in dataset')
    parser.add_argument('--production', action='store_true', help='Production mode: If true run in a separate folder on a copy of the python scripts')

    args = parser.parse_args()
    args.production = False
    path = 'data/' + args.dataset + '/' + str(args.total_images) + '/'

    data(path, args)