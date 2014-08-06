#coding=utf-8

import os, sys
import logging
import logging.handlers

#max log lenth
MAX_BYTES = 1024*1024*100

#max log files
B_COUNT = 7 

#log level
LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}



class logger:
    """
        use logging
    """

    def __init__(self, level = 'debug', logtype = 0, name = None):
        """
            level: debug/.../critical  lowest level
            type:  0 log and stdout
                   1 only log
        """

        self.logtype = logtype

        if not name:
            name = os.path.basename(sys.argv[0]).split('.')[0]

        debug_file = name+"-debug.log"
        error_file = name+"-error.log"
        
        self.debug_logger = logging.getLogger(debug_file)        
        self.error_logger = logging.getLogger(error_file)        

        level = LEVELS.get(level, logging.NOTSET)
        self.debug_logger.setLevel(level)
        
        #file rotating
        dfh = logging.handlers.TimedRotatingFileHandler(debug_file, when = 'midnight', backupCount = B_COUNT)
        efh = logging.handlers.RotatingFileHandler(error_file, maxBytes=MAX_BYTES, backupCount = B_COUNT)

        #format
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        dfh.setFormatter(self.formatter)
        efh.setFormatter(self.formatter)
  
        self.debug_logger.addHandler(dfh)
        self.error_logger.addHandler(efh)

        self.set_logtype(self.logtype)


    def set(self, level, logtype):
        level = LEVELS.get(level, logging.NOTSET)
        self.debug_logger.setLevel(level)
        self.error_logger.setLevel(level)
        if self.logtype != logtype:
            self.set_logtype(logtype)    


    def set_logtype(self, logtype):
        if logtype == 0:
            self.ch = logging.StreamHandler()
            self.ch.setFormatter(self.formatter)
            self.debug_logger.addHandler(self.ch)
            self.error_logger.addHandler(self.ch)
        elif logtype == 1 and logtype != self.logtype:
            self.debug_logger.removeHandler(self.ch)
            self.error_logger.removeHandler(self.ch)
            

    def debug(self, message):
        self.debug_logger.debug(message)


    def info(self, message):
        self.debug_logger.info(message)


    def warning(self, message):
        self.debug_logger.warning(message)
    

    def error(self, message):
        self.error_logger.error(message)


    def critical(self, message):
        self.error_logger.critical(message)



log = logger()



__all__ = ['log', 'logger']




###################TEST#######################



def test():
    argn = len(sys.argv)
    if argn > 2:
        log.set(sys.argv[1], int(sys.argv[2]))
    elif argn > 1:
        log.set(sys.argv[1], 0)
              

    print "Log testing ..."
    log.debug('This is a debug message')
    log.info('This is an info message')
    log.warning('This is a warning message')
    log.error('This is an error mesage')
    log.critical('This is a critical  mesage')
        


if __name__ == '__main__':
    test()
