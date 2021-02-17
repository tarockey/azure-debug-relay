import keras
import argparse
import horovod.keras as hvd
from keras import backend as K
import tensorflow as tf
import debugpy
from debug_utils import start_remote_debugging_from_args

hvd.init()
config = tf.ConfigProto()

#config.gpu_options.allow_growth = True
#config.gpu_options.visible_device_list = str(hvd.local_rank())

K.set_session(tf.Session(config=config))


def main():

    print("Parsing parameters")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-ds", type=str, required=True)
    parser.add_argument('--is-debug', required=False, type=bool, default=False)
    args, _ = parser.parse_known_args()

    print(f"Input folder {args.input_ds}")

    print("Horovod size:", hvd.size())
    print("Horovod rank:", hvd.rank())

    if args.is_debug and hvd.rank() == 0:
        print("Let's start debugging")
        start_remote_debugging_from_args()
        debugpy.breakpoint()


if __name__ == "__main__":
    main()
