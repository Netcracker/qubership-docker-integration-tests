import os

class FileSystem:

    def exists(self, path):
        return os.path.exists(path)

    def makedirs(self, path):
        if not self.exists(path):
            return os.makedirs(path)

    def listdir(self, path):
        return os.listdir(path)

    def remove(self, path):
        if self.exists(path):
            os.remove(path)

    def rmdir(self, path):
        if self.exists(path):
            os.rmdir(path)

    def rmtree(self, path):
        if self.exists(path):
            fsutil.rmtree(path)
