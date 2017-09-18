import argparse
from common import find_mxnet
import mxnet as mx
import time
import os
import logging
import sys
import numpy as np

import os.path
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from storage.get_iterator import get_iterator

# define classification
cls_labels = ['false positive', 'true positive']

def score(model_prefix, epoch, val_subsets, metrics, gpus, batch_size, rgb_mean, data_root,
          image_shape='1,36,36,36', data_nthreads=4):
    
    # create validation iterator
    validation_subsets = [int(k) for k in val_subsets.split(',')]
    val_iter = get_iterator(data_root, validation_subsets, batch_size = batch_size)    
    
    # create module
    sym, arg_params, aux_params = mx.model.load_checkpoint(model_prefix, epoch)
    if gpus == '':
        devs = mx.cpu()
    else:
        devs = [mx.gpu(int(i)) for i in gpus.split(',')]

    mod = mx.mod.Module(symbol=sym, context=devs)
    mod.bind(for_training=False,
             data_shapes=val_iter.provide_data,
             label_shapes=val_iter.provide_label)
    mod.set_params(arg_params, aux_params)
    if not isinstance(metrics, list):
        metrics = [metrics,]
    logging.info('Info: model scoring started...')
    total_bat = 0
    num = 0
    tic = time.time()
    
    for batch in val_iter:        
        mod.forward(batch, is_train=False)
        prob = mod.get_outputs()[0].asnumpy()
        prob = np.squeeze(prob)
        for i,p in enumerate(prob):
            a = np.argmax(p)            
            # we print the prediction results:
            logging.info('predict index=%s, probability=%f, predicted class=%s, label class=%d' %(a, p[a], cls_labels[a], batch.label[0].asnumpy()[i]))        
        for m in metrics:
            mod.update_metric(m, batch.label)
        num += batch_size
        #= this can be changed for setting the number of samples we want to evaluate.
        # comment out this block of codes will process the whole validation set
        #'''
        if num >= 1000:
            total_bat = time.time() - tic
            logging.info('%f second per image, total time: %f', total_bat/num, total_bat)
            break
        #'''
        #==============#
    return (num / (time.time() - tic), )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='score a model on a dataset')
    parser.add_argument('--model-prefix', type=str, required=True,
                        help = 'the model prefix.')
    parser.add_argument('--gpus', type=str, default='0')
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--rgb-mean', type=str, default='0,0,0')
    parser.add_argument('--val-subsets', type=str, required=True)
    parser.add_argument('--image-shape', type=str, default='1,36,36,36')
    parser.add_argument('--data-nthreads', type=int, default=4,
                        help='number of threads for data decoding')
    parser.add_argument('--epoch', type=int, default=0,
                        help='epoch of the model')
    parser.add_argument('--data_root', type=str, required=True)
    args = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    metrics = [mx.metric.create('acc')]#,
               #mx.metric.create('top_k_accuracy', top_k = 5)]

    (speed,) = score(metrics = metrics, **vars(args))
    logging.info('Finished with %f images per second', speed)
    for m in metrics:
        logging.info(m.get())