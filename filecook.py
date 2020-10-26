import os
import re 
import shutil 
import time
import datetime
import random
import sys
from PyQt5.QtWidgets import (QWidget, QCheckBox, 
                            QApplication, QHBoxLayout, 
                            QRadioButton, QFileDialog, 
                            QPushButton, QVBoxLayout, 
                            QLineEdit, QMessageBox,
                            QButtonGroup, QGridLayout,
                            QDateTimeEdit, QLabel)
# from PyQt5.QtCore import Qt


def checkpath(func):
    '''
    检查传入带改变文件的path是否有效的装饰器
    '''
    def wrapper(*args, **kwargs):
        if args:
            path = args[1]
        else:
            path = kwargs.get(path)
        if not os.path.isfile(path):
            return '{}|missing'.format(path)
        return func(*args, **kwargs)
    return wrapper

def recursive_mkdir(path):
    '''
    若不存在目标文件夹则递归创建文件夹至目标文件夹
    '''
    if not os.path.isdir(path):
        recursive_mkdir(os.path.dirname(path))
        os.mkdir(path)

class ErgodicFile():
    '''
    遍历文件夹类
    实例化时可选择传入三个参数delempty，checkson，checksize，如不传入参数则使用默认值
    :: delempty  :: 遍历后是否删除空文件夹
    :: checkson  :: 是否下钻遍历子文件夹
    :: checksize :: 遍历时是否统计文件大小，该选项大概有15%时间损耗
    '''
    def __init__(self, delempty=True, checkson=True, checksize=True):
        self.delempty = delempty # 是否删除空文件夹
        self.checkson = checkson # 是否下钻子文件夹
        self.checksize = checksize # 是否统计文件大小

        self.filesize = 0 if checksize else '未统计'

        self.countfolder = 0
        self.countfile = 0

        self.dirlist = []
        
    def ergodic(self, path): 
        '''
        接收路径，
        若接收路径不是文件夹则返回路径本身及路径的类型，
        若接收路径为文件夹则返回该文件夹下的所有文件路径及路径类型，
        若类中 self.checkson 值为 True 则遍历子文件夹，值为 False 则仅返回当前文件夹的 listdir，
        返回值为一个迭代器
        ============================
        若类中的 self.delempty 值为 True 则会在遍历后删除发现的空文件夹
        '''
        
        # print('传入迭代路径为{}'.format(path))
        path_type = 'file'
        if os.path.isfile(path):
            yield path, path_type
        elif os.path.isdir(path):
            filelist = os.listdir(path)
            while filelist or self.dirlist:
                for file in filelist:
                    filepath = os.path.join(path, file)
                    if os.path.isdir(filepath):
                        self.countfolder += 1
                        path_type = 'dir'
                        if self.checkson:
                            self.dirlist.append(filepath)
                    else:
                        self.countfile += 1
                        path_type = 'file'
                        if self.checksize:
                            self.filesize += os.path.getsize(filepath)
                    yield filepath, path_type
                filelist = []
                if self.delempty and os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)
                if self.dirlist:
                    path = self.dirlist.pop()
                    filelist = os.listdir(path)
            
    def size(self):
        units = ['B', 'K', 'M', 'G']
        if not self.checksize:
            return self.filesize
        s = self.filesize
        for i in units:
            if s > 1024:
                s /= 1024
            else:
                break
            s = round(s, 3)
        return str(s) + i

class MatchToAims():
    def __init__(self, matchrules, prefix='', suffix='', changeall=False):
        if type(matchrules) == str:
            print('in str:', matchrules)
            self.matchrules = [matchrules]
        elif type(matchrules) == list:
            self.matchrules = matchrules
        else:
            assert False, '匹配格式应为 str，或为多个 str 用 list 包裹'
        
        self.prohibit_str = r'\/:*?"<>|'

        for i in self.prohibit_str:
            if i in prefix or i in suffix:
                assert False, '输入非法字符'
        self.prefix = prefix 
        self.suffix = suffix 
        self.changeall = changeall

        self.namenum = 0

    def compile_match(self):
        res = []
        for r in self.matchrules:
            res.append(re.compile(r))
        return res

    def compile_to(self, filename):
        
        if self.prefix:
            filename = self.prefix + filename
        name, end = os.path.splitext(filename)
        if self.suffix:
            filename = name + self.suffix + end
        if self.changeall:
            if self.namenum > 0:
                filename = os.path.splitext(filename)[0] + ' ' + str(self.namenum) + end
            self.namenum += 1
        return filename 


class FileAction():
    def __init__(self, method):
        if method in ['copy', 'move', 'remove']:
            self.method = method
        else:
            assert False, "method 参数必须为 ['copy', 'move', 'remove'] 之一！"
        self.pattern = {'copy': ' cp_', 'move': ' rp_'}
        
    def repyname(self, filename):
        pattern = self.pattern.get(self.method, '')
        name, extension = os.path.splitext(filename)
        if pattern in name:
            namespt = name.split(pattern)
            try:
                newname = pattern.join(namespt[:-1]) + pattern + str(int(namespt[-1]) + 1) + extension
            except:
                newname = name + pattern + '1' + extension
        else:
            newname = name + pattern + '1' + extension
        return newname

    @checkpath
    def action(self, filepath, topath=None, newname=None):
        if self.method == 'remove':
            os.remove(filepath)
            return '{}|remove'.format(filepath)
        else:
            if not topath:
                topath = os.path.dirname(filepath)
            if not newname:
                newname = os.path.basename(filepath)
            if not os.path.isdir(topath):
                recursive_mkdir(topath)
            if hasattr(shutil, self.method):
                ac = getattr(shutil, self.method)
            while newname in os.listdir(topath):
                if os.path.dirname(filepath) != topath or self.method == 'copy':
                    newname = self.repyname(newname)
                else:
                    return '{}|{}|{}'.format(filepath, self.method,
                     'same file and dir don\'t move;and you can try "copy"')
            newpath = os.path.join(topath, newname)
            if hasattr(shutil, self.method):
                ac = getattr(shutil, self.method)
                ac(filepath, newpath)
            else:
                return 'shutil has no attr {}'.format(self.method)
            return '{}|{}|{}'.format(filepath, self.method, newpath)

class FileCook():
    def __init__(self, method, matchrules, 
                 prefix='', suffix='', 
                 chiocetime='', startime=0, endtime=0,
                 changeall=False, delempty=True, 
                 checkson=True, checksize=True):
        
        self.matchrules = matchrules
        self.chiocetime = chiocetime
        self.startime = startime
        self.endtime = endtime
        
        self.action = FileAction(method)
        self.matchtoaims = MatchToAims(matchrules, prefix, suffix, changeall)
        self.ergodic = ErgodicFile(delempty, checkson, checksize)

        self.selfpath = os.path.dirname(os.path.abspath(__file__))
        self.logpath = None

    def dellog(self, logtumbpath):
        dirname = os.path.dirname(logtumbpath)
        loglist = os.listdir(dirname)
        with open(logtumbpath, 'r') as f:
            tumblist = f.read().split('\n')
        for log in loglist:
            if log != 'logtumb':
                if os.path.join(dirname, log) not in tumblist:
                    os.remove(os.path.join(dirname, log))

    def openlog(self):
        if not self.logpath:
            t = time.strftime('{}%Y{}%m{}%d%H{}%M%S', time.localtime())
            logname = t.format(
                random.randint(1, 200), 
                random.randint(1, 200), 
                random.randint(1, 200), 
                random.randint(1, 200)
            )
            self.logpath = os.path.join(self.selfpath, 'logfolder', logname)
        return self.logpath
        
    def run_main(self, frompath, topath=None, toname=None):
        if not os.path.isfile(frompath) and not os.path.isdir(frompath):
            response = '{}|missing'.format(frompath)
            yield response
        else:
            pathiter = self.ergodic.ergodic(frompath)
            compiles = self.matchtoaims.compile_match()
            
            for path, pathtype in pathiter:
                response = ''
                if pathtype == 'file':
                    name = os.path.basename(path)
                    if self.matchrules or self.chiocetime:
                        if self.matchrules:
                            matchname = False
                            for comp in compiles:
                                if comp.match(name):
                                    matchname = True
                                    break
                        else:
                            matchname = True
                        if self.chiocetime:
                            matchtime = False
                            att = getattr(os.path, self.chiocetime)
                            filetime = att(path)
                            # print('filetime: ', filetime, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(filetime)))
                            if self.endtime >= filetime >= self.startime:
                                # print('self.startime: ', self.startime, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.startime)))
                                # print('self.endtime: ', self.endtime, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.endtime)))
                                matchtime = True 
                            else:
                                matchtime = False
                        else:
                            matchtime = True
                    else:
                        matchtime = False
                        matchname = False
                    if not toname:
                        newname = name
                    else:
                        newname = toname
                    # TODO: check time
                    if matchtime and matchname:
                        newname = self.matchtoaims.compile_to(newname)
                        response = self.action.action(path, topath=topath, newname=newname)
                        yield response
            yield '共检查文件大小：{}'.format(self.ergodic.size())
    
    def run(self, frompath, topath=None, toname=None):
        logpath = self.openlog()
        recursive_mkdir(os.path.dirname(logpath))
        with open(logpath, 'ab+') as f:
            count = 0
            for log in self.run_main(frompath, topath, toname):
                text = log + '\n'
                f.write(text.encode('UTF-8'))
                count += 1
            f.seek(-1, 1)
            f.truncate()
        if count <= 1 or os.path.getsize(logpath) == 0:
            os.remove(logpath)
        else:
            with open(os.path.join(self.selfpath, 'logfolder', 'filecooklog'), 'a+') as f:
                f.seek(0, 0)
                filecooklog = f.read().split('\n')
                if len(filecooklog) == 1 and filecooklog[0] == '':
                    filecooklog[0] = logpath
                else:
                    filecooklog.insert(0, logpath)
                if len(filecooklog) > 9:
                    dellog = filecooklog.pop()
                    try:
                        os.remove(dellog)
                    except:
                        print('{}  已不存在'.format(dellog))
            with open(os.path.join(self.selfpath, 'logfolder', 'tumblinglog'), 'a+') as f:
                f.seek(0, 0)
                tumblistlog = f.read().split('\n')
                if len(tumblistlog) == 1 and tumblistlog[0] == '':
                    tumblistlog[0] = logpath
                else:
                    tumblistlog.insert(0, logpath)
            with open(os.path.join(self.selfpath, 'logfolder', 'tumblinglog'), 'w') as f:
                f.write('\n'.join(tumblistlog))
            with open(os.path.join(self.selfpath, 'logfolder', 'filecooklog'), 'w') as f:
                f.write('\n'.join(filecooklog))
        return text
        


# if __name__ == '__main__':
#     method = 'move'
#     method = 'remove'
#     method = 'copy'
#     matchrules = [r'.+\.txt$', r'what.+']
#     prefix=''
#     suffix=''
#     toname=None
#     changeall=False
#     delempty=True
#     checkson=False
#     checksize=True
#     main = FileCook(method, matchrules, prefix, suffix, changeall, delempty, checkson, checksize)
    
#     thispath = os.path.dirname(os.path.abspath(__file__))
#     # main.run(thispath, os.path.join(thispath, 'fk'))
#     # main.run(os.path.join(thispath, 'fk'))

#     main.run(os.path.join(thispath, 'aaa'), os.path.join(thispath, 'bbb'), toname=toname)



class Tumbling():
    def __init__(self, tumbnum=0, tumbpathlist=[]):
        self.tumbnum = tumbnum 
        self.tumbpathlist = tumbpathlist
        self.dirname = os.path.dirname(os.path.abspath(__file__))
        self.logtumb = os.path.join(self.dirname, 'logfolder', 'tumblinglog')
        self.logtumblog = os.path.join(self.dirname, 'logfolder', 'actiontumblog')

        self.turn_method = {'move': 'move', 'copy': 'remove'}
        
    def tlist(self):
        if self.tumbpathlist:
            for path in self.tumbpathlist:
                yield path
        else:
            with open(self.logtumb, 'r') as f:
                tumbpathlist = f.read().split('\n')
            for i in range(self.tumbnum):
                if tumbpathlist[0]:
                    yield tumbpathlist.pop(0)
            with open(self.logtumb, 'w') as f:
                f.write('\n'.join(tumbpathlist))
                    

    def readlog(self):
        logfiles = self.tlist()
        for logfile in logfiles:
            with open(logfile, 'ab+') as f:
                while 1:
                    f.seek(-1, 1)
                    while f.tell() != 0 and f.read(1) != b'\n':
                        f.seek(-2, 1)
                    a = f.readline()
                    try:
                        res = a.decode()
                    except:
                        res = a.decode('GB2312')
                    res = res.replace('\n', '')
                    yield res
                    if f.tell() == len(a):
                        break
                    f.seek(-len(a)-1, 1)
    
    def tumback(self, text):
        if '共检查文件大小：' in text:
            return ''
        splitpath = text.split('|')
        if len(splitpath) == 3 and splitpath[1] in self.turn_method:
            tofile, method, frompath = splitpath 
            aclass = FileAction(self.turn_method.get(method))
            newname = os.path.basename(tofile)
            topath = os.path.dirname(tofile)
            response = aclass.action(frompath, topath=topath, newname=newname)
        else:
            response = '{}|该文件的已执行操作无法回滚。'.format(text)
        return response
            
    def tum_main(self):
        if os.path.isfile(self.logtumb):
            with open(self.logtumblog, 'wb+') as f:
                for text in self.readlog():
                    response = self.tumback(text)
                    if response:
                        response += '\n'
                        f.write(response.encode('UTF-8'))
                try:
                    f.seek(-1, 1)
                    f.truncate()
                except:
                    print('noting in {}'.format(self.logtumblog))
            if os.path.getsize(self.logtumb) == 0:
                os.remove(self.logtumb)
            return '前一步的文件操作已经完成恢复！'
        else:
            return '不存在可恢复文件或已恢复为有记录的最初始状态！'


# if __name__ == '__main__':
#     tb = Tumbling(1)
#     tb.tum_main()




class MatchRule(QWidget):
    '''
    前缀后缀添加框
    '''
    def __init__(self, func):
        super().__init__()
        self.func = func

        self.hb2 = QHBoxLayout()
        pretext = QLineEdit()
        precheck = QCheckBox('配括展名')
        pretext.setReadOnly(True)
        pretext.setFixedSize(30, 20)
        pretext.setObjectName('first')
        pretext.setStyleSheet("background-color:gainsboro;")
        precheck.setFixedSize(70, 20)
        precheck.stateChanged.connect(lambda: self.func(precheck, pretext))
        
        pretext2 = QLineEdit()
        precheck2 = QCheckBox('配括展名')
        pretext2.setReadOnly(True)
        pretext2.setFixedSize(30, 20)
        pretext2.setObjectName('seconed')
        pretext2.setStyleSheet("background-color:gainsboro;")
        precheck2.setFixedSize(70, 20)
        precheck2.stateChanged.connect(lambda: self.func(precheck2, pretext2))
        
        suftext = QLineEdit()
        sufcheck = QCheckBox('配包含字段')
        suftext.setReadOnly(True)
        suftext.setStyleSheet("background-color:gainsboro;")
        suftext.setObjectName('other')
        suftext.setFixedSize(90, 20)
        sufcheck.setFixedSize(80, 20)
        sufcheck.stateChanged.connect(lambda: self.func(sufcheck, suftext))
        
        self.hb2.addStretch(1)
        self.hb2.addWidget(precheck)
        self.hb2.addWidget(pretext)
        self.hb2.addStretch(1)
        self.hb2.addWidget(precheck2)
        self.hb2.addWidget(pretext2)
        self.hb2.addStretch(1)
        self.hb2.addWidget(sufcheck)
        self.hb2.addWidget(suftext)
        self.hb2.addStretch(1)

    def getcheck(self):
        return self.hb2


class Radiocheck(QWidget):
    '''
    单选按键组
    '''
    def __init__(self, textlist, func):
        super().__init__()
        
        self.func = func
        self.textlist = textlist if type(textlist) == list else [textlist]
        
        self.checkone = False
        
        self.group = QButtonGroup(self)
        self.hbx = QHBoxLayout()
        
        # for _, t in enumerate(self.textlist):
        #     self.hbx.addStretch(1)
        #     btn = QRadioButton(t)
            
        #     if not self.checkone:
        #         self.checkone = True
        #         btn.setChecked(True)
        #     btn.clicked.connect(lambda : self.func(btn))
        #     self.group.addButton(btn)
        #     self.hbx.addWidget(btn)
        b1, b2, b3 = self.textlist 
        
        btn1 = QRadioButton(b1)
        btn1.setChecked(True)
        btn1.clicked.connect(lambda : self.func(btn1))
        btn2 = QRadioButton(b2)
        btn2.clicked.connect(lambda : self.func(btn2))
        btn3 = QRadioButton(b3)
        btn3.clicked.connect(lambda : self.func(btn3))
        
        self.group.addButton(btn1)
        self.group.addButton(btn2)
        self.group.addButton(btn3)
        
        self.hbx.addStretch(1)
        self.hbx.addWidget(btn1)
        self.hbx.addStretch(1)
        self.hbx.addWidget(btn2)
        self.hbx.addStretch(1)
        self.hbx.addWidget(btn3)
        self.hbx.addStretch(1)
            
        # self.group.buttonClicked.connect(lambda : self.func(self.group))
            
    def getcheck(self):
        return self.hbx

class Checkpath(QWidget):
    '''
    文件选择器
    '''
    def __init__(self, text, name, widget, func, func2):
        super().__init__()
        
        self.cwd = os.getcwd()
        self.wid = widget
        self.func = func
        self.func2 = func2
        
        textedit = QLineEdit()
        textedit.setObjectName(name)
        if name == 'to':
            textedit.setStyleSheet("background-color:lightskyblue;")
        textedit.textChanged.connect(lambda : self.func2(textedit))
        
        sbtn = QPushButton(text, self)
        sbtn.setObjectName(name)
        sbtn.clicked.connect(lambda :self.func(self, textedit))
        
        self.hb = QHBoxLayout()
        self.hb.addWidget(textedit)
        self.hb.addWidget(sbtn)

    def getcheck(self):
        return self.hb
        
class Adpresuf(QWidget):
    '''
    前缀后缀添加框
    '''
    def __init__(self, func):
        super().__init__()
        self.func = func

        self.hb2 = QHBoxLayout()
        pretext = QLineEdit()
        precheck = QCheckBox('添加前缀')
        pretext.setReadOnly(True)
        pretext.setFixedSize(50, 20)
        pretext.setStyleSheet("background-color:gainsboro;")
        precheck.setFixedSize(70, 20)
        precheck.stateChanged.connect(lambda: self.func(precheck, pretext))
        

        suftext = QLineEdit()
        sufcheck = QCheckBox('添加后缀')
        suftext.setReadOnly(True)
        suftext.setStyleSheet("background-color:gainsboro;")
        suftext.setFixedSize(50, 20)
        sufcheck.setFixedSize(70, 20)
        sufcheck.stateChanged.connect(lambda: self.func(sufcheck, suftext))
        

        changetext = QLineEdit()
        changecheck = QCheckBox('改文件名')
        changetext.setReadOnly(True)
        changetext.setStyleSheet("background-color:gainsboro;")
        changetext.setFixedSize(80, 20)
        changecheck.setFixedSize(70, 20)
        changecheck.stateChanged.connect(lambda: self.func(changecheck, changetext))


        self.hb2.addStretch(1)
        self.hb2.addWidget(precheck)
        self.hb2.addWidget(pretext)
        self.hb2.addStretch(1)
        self.hb2.addWidget(sufcheck)
        self.hb2.addWidget(suftext)
        self.hb2.addStretch(1)
        self.hb2.addWidget(changecheck)
        self.hb2.addWidget(changetext)
        self.hb2.addStretch(1)

    def getcheck(self):
        return self.hb2

class Methocheck(QWidget):
    '''
    参数复选框
    '''
    def __init__(self, func):
        super().__init__()
        self.func = func

        self.hb = QHBoxLayout()
        
        checkBox1 = QCheckBox('删除空文件夹')
        checkBox1.setChecked(True)
        checkBox2 = QCheckBox('下钻子文件夹')
        checkBox3 = QCheckBox('统计遍历文件大小')

        checkBox1.stateChanged.connect(lambda: self.func(checkBox1))
        checkBox2.stateChanged.connect(lambda: self.func(checkBox2))
        checkBox3.stateChanged.connect(lambda: self.func(checkBox3))
        
        self.hb.addStretch(1)
        self.hb.addWidget(checkBox1)
        self.hb.addStretch(1)
        self.hb.addWidget(checkBox2)
        self.hb.addStretch(1)
        self.hb.addWidget(checkBox3)
        self.hb.addStretch(1)

    def getcheck(self):
        return self.hb
    
class MTimeWid(QWidget):
    def __init__(self, func, func2):
        super().__init__()
        self.func = func
        self.func2 = func2
        
        self.hb = QHBoxLayout()
        
        checkBox1 = QCheckBox('创建时间')
        checkBox2 = QCheckBox('修改时间')
        
        startime = QDateTimeEdit()
        startime.setReadOnly(True)
        startime.setStyleSheet("background-color:gainsboro;")
        startime.setObjectName('startime')
        startime.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        startime.setDateTime(datetime.datetime.now())
        startime.dateTimeChanged.connect(lambda: self.func2(startime))
        
        label = QLabel()
        label.setText('至')
        
        endtime = QDateTimeEdit()
        endtime.setReadOnly(True)
        endtime.setStyleSheet("background-color:gainsboro;")
        endtime.setObjectName('endtime')
        endtime.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        endtime.setDateTime(datetime.datetime.now())
        endtime.dateTimeChanged.connect(lambda: self.func2(endtime))
        
        checkBox1.stateChanged.connect(lambda: self.func(checkBox1, checkBox2, startime, endtime))
        checkBox2.stateChanged.connect(lambda: self.func(checkBox2, checkBox1, startime, endtime))
        
        self.hb.addStretch(1)
        self.hb.addWidget(checkBox1)
        self.hb.addStretch(1)
        self.hb.addWidget(checkBox2)
        self.hb.addStretch(1)
        self.hb.addWidget(startime)
        self.hb.addWidget(label)
        self.hb.addWidget(endtime)
        self.hb.addStretch(1)
        
        
    def getcheck(self):
        return self.hb 


class FilecookGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setFixedSize(500, 320)
        self.cwd = os.getcwd()
        
        self.mdict = {'复制': 'copy', '移动': 'move', '删除': 'remove',
                      '删除空文件夹': 'delempty', '下钻子文件夹': 'checkson', '统计遍历文件大小': 'checksize',
                      '添加前缀': 'prefix', '添加后缀': 'suffix', '改文件名': 'toname'}
        
        self.method = 'move'
        self.matchdict = {'first': None, 'seconed': None, 'other': None}
        
        self.chiocetime = ''
        self.chiocetime_dict = {'创建时间': 'getctime', '修改时间': 'getmtime'}
        self.twicetime = {'startime': time.time(), 'endtime': time.time()}
        
        self.pre_suf_dict = {'prefix': '', 'suffix': '', 'toname': ''}
        
        self.pfrom = None
        self.pto = None
        
        self.manychoice = {'delempty': True, 'checkson': False, 'checksize': False}
        
        self.initUI()
        
        
    def initUI(self):
        vb = QVBoxLayout()

        # sbtn = Checkpath('文件选择', 'getfiles', 'getOpenFileNames', self.selectfile).getcheck()
        sbtn1 = Checkpath('文件夹选择', 'from', 'getExistingDirectory', 
                          self.selectfile, self.pathChange).getcheck()
        
        sbtnto = Checkpath('目标文件夹', 'to', 'getExistingDirectory', 
                           self.selectfile, self.pathChange).getcheck()
        
        radio = Radiocheck(['移动','复制','删除'], self.choiceMethod).getcheck()
        match = MatchRule(self.matchName).getcheck()
        
        timehb = MTimeWid(self.checktime, self.settime).getcheck()

        hb = Methocheck(self.muchSelect).getcheck()
        hb2 = Adpresuf(self.changeName).getcheck()
        
        action = QPushButton('执行')
        action.clicked.connect(lambda :self.forwordrun())
        back = QPushButton('撤销上一次')
        back.clicked.connect(lambda :self.backwordrun())
        self.labelcount = QLabel()
        last = QHBoxLayout()
        last.addWidget(self.labelcount)
        last.addStretch(1)
        last.addWidget(action)
        last.addWidget(back)

        # vb.addLayout(sbtn)
        vb.addLayout(sbtn1)
        vb.addLayout(sbtnto)
        vb.addLayout(radio)
        vb.addLayout(match)
        vb.addLayout(timehb)
        vb.addLayout(hb)
        vb.addLayout(hb2)
        vb.addLayout(last)

        self.setLayout(vb)
        
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('文件私房烹饪')
        
        self.show()
        
    def checktime(self, button1, button2, startime, endtime):
        if button1.isChecked():
            button2.setChecked(False)
            print(self.chiocetime_dict[button1.text()])
        if button1.isChecked() or button2.isChecked():
            self.chiocetime = self.chiocetime_dict[button1.text()] if button1.isChecked() else self.chiocetime_dict[button1.text()]
            startime.setReadOnly(False)
            startime.setStyleSheet("background-color:white;")
            endtime.setReadOnly(False)
            endtime.setStyleSheet("background-color:white;")
        else:
            startime.setReadOnly(True)
            startime.setStyleSheet("background-color:gainsboro;")
            endtime.setReadOnly(True)
            endtime.setStyleSheet("background-color:gainsboro;")
            self.chiocetime = ''
        print(self.chiocetime)
        
    def settime(self, timewid):
        self.twicetime[timewid.objectName()] = time.mktime(time.strptime(timewid.text(), '%Y-%m-%d %H:%M:%S'))
        # print(time.mktime(time.strptime(timewid.text(), '%Y-%m-%d %H:%M:%S')))
        # print(time.time())
        # print(timewid.text())
        print(self.twicetime)
        
    def pathChange(self, textedit):
        if textedit.objectName() == 'from':
            self.pfrom = textedit
        else:
            self.pto = textedit
        print('frompath: '+ ('' if not self.pfrom else self.pfrom.text()))
        print('topath: ' + ('' if not self.pto else self.pto.text()))
        
    def choiceMethod(self, btns):
        # for b in btns:
        #     if b.isChecked():
        #         self.method = self.mdict.get(b.text())
        # self.method = self.mdict.get(btns.checkedButton().text())
        self.method = self.mdict.get(btns.text())
        # print(btns.checkedButton().text())
        # print(btns.text())
        print('method: ',self.method)
        
    def muchSelect(self, btn):
        if btn.isChecked():
            self.manychoice[self.mdict.get(btn.text())] = True
        else:
            self.manychoice[self.mdict.get(btn.text())] = False
        print(self.manychoice)
            
    def matchName(self, ckb, txb):
        if ckb.isChecked():
            txb.setReadOnly(False)
            txb.setStyleSheet("background-color:white;")
            self.matchdict[txb.objectName()] = txb
        else:
            txb.setReadOnly(True)
            txb.setStyleSheet("background-color:gainsboro;")
            self.matchdict[txb.objectName()] = None
        print(self.matchdict)

    def changeName(self, ckb, txb):
        if ckb.isChecked():
            txb.setReadOnly(False)
            self.pre_suf_dict[self.mdict[ckb.text()]] = txb
            txb.setStyleSheet("background-color:white;")
        else:
            txb.setReadOnly(True)
            self.pre_suf_dict[self.mdict[ckb.text()]] = ''
            txb.setStyleSheet("background-color:gainsboro;")
        print(self.pre_suf_dict)
            
    def selectfile(self, who, textedit):
        dialog = QFileDialog()
        res1 = getattr(dialog, who.wid)(self, '选取', self.cwd)
        if type(res1) == str:
            textedit.setText(res1)
        else:
            textedit.setText(';'.join(res1[0]))
        if textedit.objectName() == 'from':
            self.pfrom = textedit
        else:
            self.pto = textedit
        
    def backwordrun(self):
        reply = QMessageBox.question(self, '恢复操作', '删除操作不可恢复，是否确认恢复上一次操作？', 
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            back = Tumbling(1)
            message = back.tum_main()
        if reply == QMessageBox.Yes:
            QMessageBox.question(self, '完成', '{}'.format(message), QMessageBox.Yes)
        else:
            QMessageBox.question(self, '取消', '取消操作！', QMessageBox.Yes)
        
            
    def forwordrun(self):
        method = self.method
        matchrules = []
        for rule in self.matchdict:
            if self.matchdict[rule]:
                if rule != 'other':
                    matchrules.append('.+\.' + self.matchdict[rule].text() + '$')
                else:
                    matchrules.append('.*' + self.matchdict[rule].text() + '.*')
        prefix= '' if not self.pre_suf_dict['prefix'] else self.pre_suf_dict['prefix'].text()
        suffix = '' if not self.pre_suf_dict['suffix'] else self.pre_suf_dict['suffix'].text()
        
        chiocetime=self.chiocetime
        startime=self.twicetime['startime']
        endtime=self.twicetime['endtime']
        
        toname = '' if not self.pre_suf_dict['toname'] else self.pre_suf_dict['toname'].text()
        
        changeall = True if toname else False
        delempty = self.manychoice['delempty']
        checkson = self.manychoice['checkson']
        checksize = self.manychoice['checksize']
        
        frompath = '' if not self.pfrom else self.pfrom.text()
        topath = '' if not self.pto else self.pto.text()
        
        reply = QMessageBox.Yes
        if self.method == 'remove':
            reply = QMessageBox.question(self, '删除操作', '删除操作不可恢复，确认删除吗？', 
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            main = FileCook(method, matchrules, prefix, suffix, chiocetime, startime, endtime, changeall, delempty, checkson, checksize)

            totalcount = main.run(frompath, topath, toname=toname)
        if reply == QMessageBox.Yes:
            QMessageBox.question(self, '完成', '操作完成！', QMessageBox.Yes)
            self.labelcount.setText('本次执行' + totalcount)
        else:
            QMessageBox.question(self, '取消', '取消操作！', QMessageBox.Yes)
        
        # print('method: ', method, 
        # 'matchrules: ', matchrules, 
        # 'prefix: ', prefix, 
        # 'suffix: ', suffix,
        # 'toname: ', toname,
        # 'changeall: ', changeall,
        # 'delempty: ', delempty,
        # 'checkson: ', checkson,
        # 'checksize: ', checksize,
        # 'frompath: ', frompath, 
        # 'topath: ', topath)
            
app = QApplication(sys.argv)
mainwindow = FilecookGUI()
sys.exit(app.exec_())
