import numpy as np

# different valid image sets
VALID_DATASETS = ['baby', 'MNIST', 'BW', 'TEXCOL']
def get_images(name='baby', length=1, size=(28,28)):
    """Get images from datasets

    Args:
    ----------
        name (str, optional): name of dataset to be get. Defaults to 'baby'.\n
        length (int, optional): number of images from the dataset to get. Defaults to 1.\n
        size (tuple, optional): size of the images to get, will resize if needed. Defaults to (28,28).

    Raises:
    ----------
        ValueError: if name is not one of 'baby', 'MNIST', 'BW', 'TEXCOL'

    Returns:
    ----------
        [img1, img2]: list of images (or suitable type of list)
    """
    if name not in VALID_DATASETS:
        raise ValueError(f"name must be one of {VALID_DATASETS}")
    
    from skimage.io import imread
    from skimage.transform import resize
    if name == 'baby':
        img_baby = imread("data/test/3.jpg",0) # hardcoded colour, make bw outside
        img_baby = resize(img_baby, size)
        return [img_baby]
    
    elif name == 'MNIST':
        from torchvision import datasets
        mnist = datasets.MNIST('data', train=True, download=True)
        imgs = [resize(np.asarray(mnist[i][0]), size) for i in range(length)]
        return imgs
    
    import os
    import pickle
    if name == 'BW':
        # TODO: resize images
        # TODO: better params for creating of images
        # TODO: enforce a ratio of white/black?
        path = 'data/BWv1.pkl'
        if os.path.isfile(path):
            with open (path, 'rb') as fp:
                imgs = pickle.load(fp)
                diff = length - len(imgs)
                if diff < 0:
                    return imgs[:length]
                else:
                    imgs = imgs + create_bw(diff, size) # append new images
        else:
            imgs = create_bw(length, size) # or create all images
        with open(path, 'wb') as fp:
            pickle.dump(imgs, fp) # will truncate if neccessary
        return imgs
    elif name == 'TEXCOL':
        # TODO: resize images
        # TODO: better params for creating of images
        # TODO: check if texture folders is present (download if neccessary)
        from glob import glob
        from generate_dataset import make_texture_colour_image
        
        cmaps = ['Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds']
        folder_path = 'data/textures/Normalized Brodatz'
        extension = '.tif'
        imgs = glob(os.path.join(folder_path,'*'+extension))
        
        path = 'data/TEXCOLv1.pkl'
        if os.path.isfile(path):
            with open (path, 'rb') as fp:
                outputs = pickle.load(fp)
                diff = length - len(outputs)
                if diff < 0:
                    return outputs[:length] # slice across each to length
                else:
                    length = diff # will create diff number below
        else: # do we have some existing?
            outputs = []
            
        for i in range(length): # create all required images
            outputs.append(make_texture_colour_image(imgs, cmaps))
        with open(path, 'wb') as fp:
            pickle.dump(outputs, fp)
        return outputs
    
def create_bw(length, size, ratio=None):
    import random
    
    outputs = []
    for i in range(length):
        w,h = (random.randint(size[0]//3, size[0]), random.randint(size[0]//3, size[0]))
        x,y = (random.randint(size[0]//3, size[0]), random.randint(size[0]//3, size[0]))

        xy = [(x-w//2,y-h//2), (x+w//2,y+h//2)]
        answer = np.zeros(size)
        answer[xy[0][0]:xy[1][0], xy[0][1]:xy[1][1]] = 255
        outputs.append(answer)
        
    return outputs 

def add_headers(
    fig,
    *,
    row_headers=None,
    col_headers=None,
    row_pad=1,
    col_pad=5,
    rotate_row_headers=True,
    **text_kwargs
):
    # Based on https://stackoverflow.com/a/25814386

    axes = fig.get_axes()

    for ax in axes:
        sbs = ax.get_subplotspec()

        # Putting headers on cols
        if (col_headers is not None) and sbs.is_first_row():
            ax.annotate(
                col_headers[sbs.colspan.start],
                xy=(0.5, 1),
                xytext=(0, col_pad),
                xycoords="axes fraction",
                textcoords="offset points",
                ha="center",
                va="baseline",
                **text_kwargs,
            )

        # Putting headers on rows
        if (row_headers is not None) and sbs.is_first_col():
            ax.annotate(
                row_headers[sbs.rowspan.start],
                xy=(0, 0.5),
                xytext=(-ax.yaxis.labelpad - row_pad, 0),
                xycoords=ax.yaxis.label,
                textcoords="offset points",
                ha="right",
                va="center",
                rotation=rotate_row_headers * 90,
                **text_kwargs,
            )

def plot_images(imgs, labels=None, row_headers=None, col_headers=None, colmns=None, title=None):
    """
    imgs = [img1, img2]
    labels = ['label1', 'label2']
    colmns = 2 (so will be a 1x2 size display)
    """
    import matplotlib.pyplot as plt
    
    num = len(imgs)
    # Calculate the given number of subplots, or use colmns count to get a specific output
    if colmns is None:
        ay = np.ceil(np.sqrt(num)).astype(int) # this way it will prefer rows rather than columns
        ax = np.rint(np.sqrt(num)).astype(int)
    else:
        ax = np.ceil(num / colmns).astype(int)
        ay = colmns
        
    fig = plt.figure()
    if title is not None:
        fig.suptitle(title, fontsize=16)
    
    for i in range(1, num+1):
        sub = fig.add_subplot(ax,ay,i)
        if labels is not None:
            sub.set_title(f'{labels[i-1]}')
            
        sub.axis('off')
        sub.imshow(imgs[i-1])
        
    add_headers(fig, row_headers=row_headers, col_headers=col_headers, rotate_row_headers=False)
    # plt.tight_layout()

# different weighting functions
def get_weights(img, choice=0, radius=10, sigmaI=0.1, sigmaX=1):
    """For an image, get the weights matrix W for the image

    Args:
        img (Array): the img to convert to weights
        choice (int, optional): Which weight func to use, instead of names uses number system. Defaults to 1.
        
        choices correspond to: 
        [manual_weights_binary, manual_weights_abs, intensity_weight_matrix, weights_2,
        positional_weight_matrix, intens_posit_wm, weight_tot, weight_int, weight_dist]

    Returns:
        Array: W, weights matrix (or affinity matrix depending on who you ask :) )
    """
    from functools import partial
    # TODO: use these :)
    from nc_suite import manual_weights_binary, manual_weights_abs # radius
    from nc_suite import weights_2 # radius, sigmas
    from nc_suite import intensity_weight_matrix, positional_weight_matrix, intens_posit_wm
    # TODO: verify these ones work (does the formula make sense)
    from nc_suite import weight_tot, weight_int, weight_dist # test radius, sigmas 
    from nc_suite import generic_weight, generic_weight_noexp, generic_weight_rawfunc # test params
    from nc_suite import colour_diff, texture_diff
    
    # colour_func = partial()
    texture_func = partial(texture_diff, neighborhood_size=radius)
    
    choices = [partial(manual_weights_binary, r=radius),                            # 0
               partial(manual_weights_abs, r=radius),                               # 1
                       intensity_weight_matrix,                                     # 2
                partial(weights_2,r=radius, sigma_I=sigmaI, sigma_X=sigmaX),        # 3
                       positional_weight_matrix,                                    # 4
                       intens_posit_wm,                                             # 5
                partial(weight_tot,radius=radius, sigmaI=sigmaI, sigmaX=sigmaX),    # 6
                partial(weight_int,radius=radius, sigmaI=sigmaI),                   # 7
                partial(weight_dist,radius=radius, sigmaX=sigmaX),                  # 8
                partial(generic_weight, radius=radius, func=texture_func,           # 9
                                        sigmaI=sigmaI, sigmaX=sigmaX),
                partial(generic_weight, radius=radius, func=colour_diff,            # 10
                                        sigmaI=sigmaI, sigmaX=sigmaX),
                partial(generic_weight_noexp, radius=radius, func=texture_func,     # 11
                                        sigmaX=sigmaX),
                partial(generic_weight_noexp, radius=radius, func=colour_diff,      # 12
                                        sigmaX=sigmaX),
                partial(generic_weight_rawfunc, radius=radius, func=texture_func),  # 13
                partial(generic_weight_rawfunc, radius=radius, func=colour_diff),   # 14
                ]
    
    func = choices[choice]
    W = func(img)
    # TODO: W = W / np.max(W), but might be better as a pre-process func... :)
    return W


# different laplace solvers
# cheap, expensive, symmetric/none...
# how to handle 0's in D? or... how to handle 0's in d?

# Also, specify different pre, eig, post as a list of functions which get applied by looping..

# different eigensolvers
# initially try for just one eig solver?
# Time the eigensolvers

# linalg.eig(L)
# np.eig(L)

# linalg.eigh(L)
# linalg.eig(L)
# linalg.eigh(L,D)
# linalg.eig(L,D)
# + the gvd variants etc....

# outputs
# - * 28, * eigval, * np.sqrt(D)
# sign of outputs to make it an indicator vector
# objective, eqconst