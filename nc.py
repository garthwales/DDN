import torch
import numpy as np
import matplotlib.pyplot as plt

# local imports
from node import *

# NOTE: for all einsums, b/bc could be replaced with an ellipse ...

def manual_weight(name, r=1, minVer=False):
    """
    I = Image name
    r = radius for connections (defaults to 4-way connection with r=1)
    """
    if type(name) == str: 
        I = plt.imread(name)
        B = 1
        x,y = I.shape
    else: 
        I = name
        B,C,x,y = I.shape
    
    N = x*y
    diags = r+1 if minVer else N
    W = torch.zeros((B,N,N))

    r = min(N//2, r) # ensure the r value doesn't exceed the axes of the outputs

    # TODO : the minVer and non-minver versions could be combined... diags placed into W's size tuple etc and math
    # e.g. something like https://stackoverflow.com/a/43311126 or similar utilised
    I = I.flatten()
    for b in range(0, B):
        for u in range(N): # could use step size of r to improve speed?
            end = min(u+r+1, N) # upper triangle, only traverse as far as needed
            for v in range(u,end):
                if np.linalg.norm(u-v) > r: # 4-way connection
                    continue
                # Symmetric
                W[b][u][v] = 1 if I[u + b*N] == I[v + b*N] else 0
                W[b][v][u] = 1 if I[u + b*N] == I[v + b*N] else 0

    # testing = False # NOTE: will need to remove channels portion if using again
    # if testing:
    #     W_test = torch.zeros((B,C,N,N))
    #     for b in range(0, B):
    #         for c in range(0, C):
    #             for u in range(N):
    #                 for v in range(N):
    #                     if np.linalg.norm(u-v) > r: # 4-way connection
    #                         continue
    #                     # Symmetric
    #                     W_test[b][c][u][v] = 1 if I[u + c*N + b*N] == I[v + c*N + b*N] else 0
    #                     W_test[b][c][v][u] = 1 if I[u + c*N + b*N] == I[v + c*N + b*N] else 0
    #     print(torch.allclose(W, W_test))
    
    if minVer:
        # This will create an output which is just the important non-zero diagonals
        # should make learning much easier (3x1024 vs 1024x1024)
        out = torch.zeros((B,r,N)) # r, not r+1 as the diagonal is always 1 in current scheme. same reason for range(1,...)
        for b in range(B):
            for index, i in enumerate(range(1, diags)): # symmetric, so grabbing only upper tri diagonals
                temp_diag = torch.diag(W[b],i)
                pad = torch.zeros(N-len(temp_diag)) # pad with 0's to make it so it will fit
                out[b][index] = torch.cat([temp_diag, pad])
        W = out # size is [1,r,N]
    return W

def de_minW(out):
    """
    Returns the reconstructed weight matrix from a smaller version.
    """

    # Currently this works on a [r, N] matrix
    # could use https://stackoverflow.com/a/68029042 to
    # work on an [N*N] 1d matrix... and would require less actual code?
    # would be much more computationally friendly..

    B,r,N = out.shape
    if r == N: # if already square, then don't bother
        return out

    reconst = torch.zeros((B,N,N), device=out.device)
    diags = r + 1 # include the main diagonal of ones
    for b in range(B):
        for i  in range(0, diags):
            if i == 0: # add the main diagonal (of all ones)
                reconst[b] = torch.add(reconst[b], torch.eye(N, device=out.device))
            else: # add the symmetric non-main diagonals
                diagonal = out[b][i-1]
                temp = torch.diag(diagonal[:N-i], i).to(out.device) # [:N-i] trims to fit the index'th diag size, places into index'th place
                reconst[b] = torch.add(reconst[b], temp) # add the upper diagonal (or middle if 0)
                temp = torch.diag(diagonal[:N-i], -i).to(out.device)
                reconst[b] = torch.add(reconst[b], temp) # add the lower diagonal (symmetric)
    return reconst

def check_symmetric(a, rtol=1e-05, atol=1e-08): # defaults of allclose
    return torch.allclose(a, a.transpose(-2,-1), rtol, atol)

class NormalizedCuts(AbstractDeclarativeNode):
    """
    A declarative node to embed Normalized Cuts into a Neural Network
    
    Normalized Cuts and Image Segmentation https://people.eecs.berkeley.edu/~malik/papers/SM-ncut.pdf
    Shi, J., & Malik, J. (2000)
    """
    def __init__(self, chunk_size=None, eps=1e-12, gamma=None):
        super().__init__(chunk_size=chunk_size, eps=eps, gamma=gamma) # input is divided into chunks of at most chunk_size
        
    def objective(self, x, y):
        """
        f(W,y) = y^T * (D-W) * y / y^T * D * y

        Arguments:
            y: (b, c, x, y) Torch tensor,
                batch, channels of solution tensors

            x: (b, c, N, N) Torch tensor,
                batch, channels of affinity/weight tensors (N = x * y)        

        Return value:
            objectives: (b, c, x) Torch tensor,
                batch, channels of objective function evaluations
        """
        # x = de_minW(x) # check if needs to be converted from minVer style

        y = y.flatten(-2) # converts to the vector with shape = (32, 1, N) 
        b, N = y.shape
        y = y.reshape(b,1,N) # convert to a col vector

        d = torch.einsum('bij->bj', x) # eqv to x.sum(0) --- d vector
        D = torch.diag_embed(d) # D = matrix with d on diagonal

        L = D-x

        return torch.div( # TODO: fix this
            torch.einsum('bij,bkj->bik', torch.einsum('bij,bkj->bik', y, L), y),
            torch.einsum('bij,bkj->bik', torch.einsum('bij,bkj->bik', y, D), y)
        ).squeeze(-2)

    
    def equality_constraints(self, x, y):
        """
        subject to y^T * D * 1 = 0

        Arguments:
            y: (b, c, x, y) Torch tensor,
                batch, channels of solution tensors

            x: (b, c, N, N) Torch tensor,
                batch, channels of affinity/weight tensors (N = x * y)        

        Return value:
            equalities: (b, c, x) Torch tensor,
                batch, channel of constraint calculation scalars
        """
        # x = de_minW(x) # check if needs to be converted from minVer style

        y = y.flatten(-2) # converts to the vector with shape = (32, 1, N) 
        b, c, N = y.shape
        y = y.reshape(b,c,1,N) # convert to a col vector (y^T)

        d = torch.einsum('bij->bj', x) # eqv to x.sum(0) --- d vector
        D = torch.diag_embed(d).to(device=y.device) # D = matrix with d on diagonal
        ONE = torch.ones(b,c,N,1).to(device=y.device) # create a vector of ones

        # MATRIX SIZES (for sanity check)
        # B,C,1,N
        # B,C,N,N
        # = B,C,1,N
        # B,C,N,1
        # = B,C,1,1

        # return the constraint calculation, squeezed to output size
        return torch.einsum('bIK,bKJ->bIJ', torch.einsum('bIK,bKJ->bIJ',y, D), ONE).squeeze(-2)

    def solve(self, A):
        """ 
        Solve the normalized cuts using eigenvectors (produces single cut, no recursion yet)

        Arguments:
            A: (b, c, N, N) Torch tensor,
                batch, channels of affinity/weight tensors (N = x * y from orignal x,y images)

        TODO: pass a parameter to avoid hardcoded output dimensions
        """        
        # Implementation notes:
        # - requires einsum's to act on batch. Otherwise torch complains about tensors not being in graph being differentiated
            # TODO: check if above claim is true still since refactoring
        # - inf in D_inv_sqrt don't matter as other functions used seem to handle it fine, previously avoided by only inverting the diagonal

        A = A.detach() # TODO : verify if this breaks anything

        A = de_minW(A) # check if needs to be converted from minVer style
        b,x,y = A.shape
        out_size = int(np.sqrt(x)) # NOTE: assumes it is square..
        output_size = (b,out_size,out_size)

        # can also replace bc with ...
        d = torch.einsum('bij->bj', A) # eqv to A.sum(0) --- d vector
        D = torch.diag_embed(d) # D = matrix with d on diagonal
        D_inv_sqrt = torch.diag_embed(d.pow(-0.5)) # previously had pow inside diag

        L = D-A # Laplacian matrix
        # The symmetrically normalized laplacian can be calculated as D^-0.5 * L * D^-0.5 or eqv. I - D^-0.5 * A * D^-0.5 
        L_norm = torch.einsum('...ij,...jk->...ik', torch.einsum('...ij,...jk->...ik', D_inv_sqrt , L) , D_inv_sqrt)
        L_norm = L_norm.to(A.device) # TODO : more elegant fix?

        # Solve eigenvectors and eigenvalues
        (w, v) = torch.linalg.eigh(L_norm)
        
        # Returns the second smallest eigenvector
        output = v[:,:,1,None].reshape(output_size).requires_grad_(True)
        # DNN NOTE: Detach inputs from graph, attach only the output (or if using optimisation to solve you can with torch.enable_grad() ( ... optim ))
        return output, None
    
    def test(self, x, y):
        """ Test gradient """
        # Evaluate objective function at (xs,y):
        f = torch.enable_grad()(self.objective)(x, y=y) # b

        # Compute partial derivative of f wrt y at (xs,y):
        fY = grad(f, y, grad_outputs=torch.ones_like(f), create_graph=True)
        return fY

if __name__ == "__main__":
    from torchvision import transforms
    from net_argparser import net_argparser
    from data import SimpleDatasets, plot_multiple_images

    # 0.1 - quick checks that the node does the correct outputs
    args = net_argparser()
    device = torch.device(f'cuda:{args.gpu}' if torch.cuda.is_available() else 'cpu')
    print(f'Using device {device}')

    print(f'r:\t{args.radius}\nmin:\t{args.minify}\nsize:\t{args.img_size}')

    train_dataset = SimpleDatasets(args, transform=transforms.ToTensor())
    input, output, weight = train_dataset.get_image(0)[None,:], train_dataset.get_segmentation(0), train_dataset.get_weights(0)
    sample=[input, output, de_minW(weight)]
    W_1 = manual_weight(input, args.radius, False)
    W_2 = manual_weight(input, args.radius, True)
    W_3 = de_minW(W_2)
    print(f'conversion to/from consistent (dataset input): {str(torch.allclose(W_1, W_3))}')
    if args.minify:
        print(f'creation/loading consistent (minified): {str(torch.allclose(weight, W_2))}')
    print(f'creation/loading consistent (full): {str(torch.allclose(de_minW(weight), W_1))}')

    node = NormalizedCuts()
    y,misc = node.solve(weight)
    sample.append(y)
    plot_multiple_images('test cut', sample, dir='experiments/nc/')

    # 0.2 - Misc checks...
    print("\nCheck minified converts to correct full form")
    A = torch.randn(3,1,3)
    print(A[0][0])
    full_A = de_minW(A)
    print(full_A[0][0])
    print(f'is symmetric: {str(check_symmetric(full_A))}')

    print("\nCheck manual_weight and deMinW provide consistent output")
    A = torch.randn(2,2,3,3)
    W_1 = manual_weight(A, 1, False)
    W_2 = manual_weight(A, 1, True)
    W_3 = de_minW(W_2)
    print(f'conversion to/from consistent: {str(torch.allclose(W_1, W_3))}')

    # 1. Confirm the node can calculate a first derivative (eg. does pytorch complain about anything?)
    print("\nstandard tests")
    A = torch.randn(32,1024,1024, requires_grad=True, device=device) # real 32x32 image input

    A = torch.nn.functional.relu(A) # enforce positive constraint
    A_t = torch.einsum('bij->bji', A) # transpose of batched matrix
    A = torch.matmul(A, A_t) # to create a positive semi-definite matrix

    node = NormalizedCuts()
    y,misc = node.solve(A)
    node.test(A,y=y)

    # 2. Confirm the node solves the correct problems
    eqconstBool = issubclass(NormalizedCuts, EqConstDeclarativeNode) # If AbstractDeclarativeNode then false, remove this later?...
    fSolved = node.objective(A, y)
    print(f'objective - Max: {torch.max(fSolved)}, Min: {torch.min(fSolved)}, Mean: {torch.mean(fSolved)}, std var: {torch.std(fSolved)}')
    if eqconstBool:
        # TODO: verify why this is not correct?
        fConsts = node.equality_constraints(A, y)
        print(f'eqconst - Max: {torch.max(fConsts)}, Min: {torch.min(fConsts)}, Mean: {torch.mean(fConsts)}, std var: {torch.std(fConsts)}')

    print('\nminVer tests')
    # 3. Confirm the node can calculate a first derivative (eg. does pytorch complain about anything?)
    #    for the minVer style
    # TODO: fix this bit? or at least debug it a little
    A = torch.randn(32,2,1024, requires_grad=True, device=device)
    A = torch.nn.functional.relu(A) # enforce positive constraint

    node = NormalizedCuts()
    y,misc = node.solve(A)
    node.test(de_minW(A),y=y)

    # 4. Confirm the node solves the correct problems
    eqconstBool = issubclass(NormalizedCuts, EqConstDeclarativeNode) # If AbstractDeclarativeNode then false, remove this later?...
    fSolved = node.objective(A, y)
    print(f'objective - Max: {torch.max(fSolved)}, Min: {torch.min(fSolved)}, Mean: {torch.mean(fSolved)}, std var: {torch.std(fSolved)}')
    if eqconstBool:
        # TODO: verify why this is not correct?
        fConsts = node.equality_constraints(A, y)
        print(f'eqconst - Max: {torch.max(fConsts)}, Min: {torch.min(fConsts)}, Mean: {torch.mean(fConsts)}, std var: {torch.std(fConsts)}')

    