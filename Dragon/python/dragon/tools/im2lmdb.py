# --------------------------------------------------------
# Dragon
# Copyright(c) 2017 SeetaTech
# Written by Ting Pan
# --------------------------------------------------------

""" Generate LMDB from images """

import os
import sys
import time
import shutil
import argparse

import cv2
try:
    import numpy as np
except: pass

from dragon.tools.db import LMDB
from dragon.vm.caffe.proto import caffe_pb2

def resize_image(im, resize):
    if im.shape[0] > im.shape[1]:
        newsize = (resize, im.shape[0] * resize / im.shape[1])
    else:
        newsize = (im.shape[1] * resize / im.shape[0], resize)
    im = cv2.resize(im, newsize)
    return im

def make_db(args):
    if os.path.isfile(args.list) is False:
        raise ValueError('the path of image list is invalid.')
    if os.path.isdir(args.database) is True:
        raise ValueError('the database is already exist or invalid.')

    print('start time: ', time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime()))

    db = LMDB(max_commit=10000)
    db.open(args.database, mode='w')

    total_line = sum(1 for line in open(args.list))
    count = 0
    zfill_flag = '{0:0%d}' % (args.zfill)

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), args.quality]

    start_time = time.time()

    with open(args.list, 'r') as input_file:
        records = input_file.readlines()
        if args.shuffle:
            import random
            random.shuffle(records)

        for record in records:
            count += 1
            if count % 10000 == 0:
                now_time = time.time()
                print('{0} / {1} in {2:.2f} sec'.format(
                    count, total_line, now_time - start_time))
                db.commit()

            record = record.split()
            path = record[0]
            label = record[1]

            img = cv2.imread(os.path.join(args.root, path))
            if args.resize > 0:
                img = resize_image(img, args.resize)
            if args.pad > 0:
                pad_img = np.zeros((img.shape[0] + 2 * args.pad,
                                    img.shape[1] + 2 * args.pad, 3), dtype=img.dtype)
                pad_img[args.pad : args.pad + img.shape[0],
                        args.pad : args.pad + img.shape[1], :] = img
                img = pad_img
            result, imgencode = cv2.imencode('.jpg', img, encode_param)

            datum = caffe_pb2.Datum()
            datum.height, datum.width, datum.channels = img.shape
            datum.label = int(label)
            datum.encoded = True
            datum.data = imgencode.tostring()
            db.put(zfill_flag.format(count - 1), datum.SerializeToString())

    now_time = time.time()
    print('{0} / {1} in {2:.2f} sec'.format(count, total_line, now_time - start_time))
    db.put('size', str(count))
    db.put('zfill', str(args.zfill))
    db.commit()
    db.close()

    shutil.copy(args.list, args.database + '/image_list.txt')
    end_time = time.time()
    print('{0} images have been stored in the database.'.format(total_line))
    print('This task finishes within {0:.2f} seconds.'.format(end_time - start_time))
    print('The size of database is {0} MB.'.
          format(float(os.path.getsize(args.database + '/data.mdb') / 1000 / 1000)))


def parse_args():
    parser = argparse.ArgumentParser(description='Create LMDB from images for classification.')
    parser.add_argument('--root', help='the root folder of raw images')
    parser.add_argument('--list', help='the filepath of image list')
    parser.add_argument('--database', help='the filepath of database')
    parser.add_argument('--zfill', type=int, default=8, help='zfill for the key of database')
    parser.add_argument('--resize', type=int, default=0, help='resize the shorter edge of image to the newsize')
    parser.add_argument('--pad', type=int, default=0, help='zero-pad the image')
    parser.add_argument('--quality', type=int, default=95, help='JPEG quality for encoding, 1-100')
    parser.add_argument('--shuffle', type=bool, default=True, help='randomize the order in list file True')

    if len(sys.argv) < 4:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

if __name__ == '__main__':

    args = parse_args()

    make_db(args)