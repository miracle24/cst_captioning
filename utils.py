import sys
import os
import json

import numpy as np
from collections import OrderedDict

sys.path.append('coco-caption')
from pycocotools.coco import COCO
from pycocoevalcap.eval import COCOEvalCap

# Input: seq, N*D numpy array, with element 0 .. vocab_size. 0 is END token.
def decode_sequence(ix_to_word, seq):
    N, D = seq.size()
    out = []
    for i in range(N):
        txt = ''
        for j in range(D):
            ix = seq[i,j]
            if ix > 0 :
                if j >= 1:
                    txt = txt + ' '
                txt = txt + ix_to_word[ix]
            else:
                break
        out.append(txt)
    return out

def language_eval(gold_file, pred_file):
    
    # save the current stdout
    temp = sys.stdout 
    sys.stdout = open(os.devnull, 'w')

    coco = COCO(gold_file)
    cocoRes = coco.loadRes(pred_file)
    cocoEval = COCOEvalCap(coco, cocoRes)
    cocoEval.params['image_id'] = cocoRes.getImgIds()
    cocoEval.evaluate()

    out = {}
    for metric, score in cocoEval.eval.items():
        out[metric] = round(score, 3)

    # restore the previous stdout    
    sys.stdout = temp
    return out


def array_to_str(arr):
    out = ''
    for i in range(len(arr)):
        if arr[i] == 0:
            break
        if arr[i] == 1:    
            continue
        out += str(arr[i]) + ' '
    return out.strip()

def get_self_critical_reward(model_res, greedy_res, data_gts, CiderD_scorer):
    batch_size = model_res.size(0)

    res = OrderedDict()
    
    model_res = model_res.cpu().numpy()
    greedy_res = greedy_res.cpu().numpy()
    for i in range(batch_size):
        res[i] = [array_to_str(model_res[i])]
    for i in range(batch_size):
        res[batch_size + i] = [array_to_str(greedy_res[i])]

    gts = OrderedDict()
    for i in range(len(data_gts)):
        gts[i] = [array_to_str(data_gts[i][j]) for j in range(len(data_gts[i]))]

    #_, scores = Bleu(4).compute_score(gts, res)
    #scores = np.array(scores[3])
    res = [{'image_id':i, 'caption': res[i]} for i in range(2 * batch_size)]
    gts = {i: gts[i % batch_size] for i in range(2 * batch_size)}
    
    ciderd_score, scores = CiderD_scorer.compute_score(gts, res)

    #import pdb; pdb.set_trace()
    
    scores = scores[:batch_size] - scores[batch_size:]

    rewards = np.repeat(scores[:, np.newaxis], model_res.shape[1], 1)
    
    return rewards, ciderd_score
