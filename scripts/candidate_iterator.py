import os, argparse, random, helper
import mxnet as mx
import numpy as np


class CandidateIter(mx.io.DataIter):
    def __init__(self, root, subsets, batch_size = 1, data_name = 'data', label_name = 'softmax_label', shuffle = True, chunk_size = 1000):
        self.data_files = []
        self.label_files = []
        for subset in subsets:
            self.data_files.append(os.path.join(root, "subset%d" % subset, "data.npy"))
            self.label_files.append(os.path.join(root, "subset%d" % subset, "labels.npy"))

        if shuffle:
            random.seed(42)
            random.shuffle(self.data_files)
            random.seed(42)
            random.shuffle(self.label_files)

        self.shuffle = shuffle
        self.root = root
        self.batch_size = batch_size
        self.chunk_size = chunk_size
        self.data_name = data_name
        self.label_name = label_name
        self.reset()

    def get_current_iterator(self):
        while self.__iterator is None:
            if self.current_file >= len(self.data_files):
                raise StopIteration

            data = np.memmap(self.data_files[self.current_file], dtype = helper.DTYPE, mode = "r")
            labels = np.memmap(self.data_files[self.current_file], dtype = helper.DTYPE, mode = "r")

            start = self.current_chunk * self.chunk_size * self.batch_size
            end = min((self.current_chunk + 1) * self.chunk_size * self.batch_size, data.shape[0])

            self.current_chunk += 1

            if end - start <= self.batch_size:
                self.current_chunk = 0
                self.current_file += 1
                continue

            data_chunk = data[start:end, :, :, :]
            label_chunk = labels[start:end]

            self.__iterator = mx.io.NDArrayIter(data = data_chunk, label = label_chunk, batch_size = 30, shuffle = self.shuffle)

        return self.__iterator

    def __iter__(self):
        return self

    def reset(self):
        self.current_file = 0
        self.current_chunk = 0
        self.__iterator = None

    def __next__(self):
        return self.next()

    @property
    def provide_data(self):
        return self.get_current_iterator().provide_data()

    @property
    def provide_label(self):
        return self.get_current_iterator().provide_label()

    def next(self):
        result = None
        while result is None:
            iterator = self.get_current_iterator()
            try:
                result = iterator.next()
            except StopIteration:
                self.__iterator = None
        return result


def main(args):
    data_iter = CandidateIter(args.root, args.subsets, batch_size = 30)
    for batch in data_iter:
        print batch.data
        assert len(batch.data) == 30
        print batch.label
        assert len(batch.label) == 30
        print batch.pad


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "test the dataset iterator")
    parser.add_argument("root", type=str, help="folder containing prepared dataset folders")
    parser.add_argument("--subsets", type=int, nargs="*", help="the subsets which should be processed", default = range(0, 10))
    main(parser.parse_args())

