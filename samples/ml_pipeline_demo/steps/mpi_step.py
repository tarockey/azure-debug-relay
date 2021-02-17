import keras
import argparse
import horovod.keras as hvd
from keras import backend as K
import tensorflow as tf
            

hvd.init()
config = tf.ConfigProto()

#config.gpu_options.allow_growth = True
#config.gpu_options.visible_device_list = str(hvd.local_rank())

K.set_session(tf.Session(config=config))


def main():

    print("Parsing parameters")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_ds", type=str, required=True)
    parser.add_argument("--is_debug", type=bool, required=True)
    args, _ = parser.parse_known_args()

    print(f"Input folder {args.input_ds}")
    print(f"Debug flag {args.is_debug}")

    print("Horovod size:",hvd.size())
    print("Horovod rank:", hvd.rank())

    if args.is_debug and hvd.rank()==0:
        print("Let's start debugging")
        # TODO: Add debug relay connect code here 

if __name__ == "__main__":
    main()