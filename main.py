# -*- coding: utf-8 -*-
# /usr/bin/env python3

import sys
import json
import traceback
import time
import os

from PyQt6.QtWidgets import QApplication, QWidget,QTableWidgetItem,QDialog,QMainWindow,QMessageBox,QFileDialog,QHeaderView, QSystemTrayIcon,QMenu
from PyQt6.QtGui import QIcon,QAction
from PyQt6.QtCore import Qt

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from win32com.client import Dispatch

from MainWindowUI  import Ui_MainWindow
from InputDialogUI import Ui_InputDialog
from file_delete import FileDelete
from logger_conf import init_logger,QTextEditHandler

import resource_rc # type: ignore
 

class AutoStart():
    
    def __init__(self) -> None:
        self.exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
    
    """创建自动启动快捷方式"""
    def auto_start_on(self):
        """创建自启快捷方式"""
        self.create_shortcut(self.get_shortcut_create_path())
        
    def auto_start_off(self):
        """删除自启快捷方式"""
        #获取快捷方式的位置，然后再尝试删除
        self.delete_shortcut(self.get_shortcut_create_path())

    def get_shortcut_create_path(self):
        # 获取当前系统用户名和快捷方式创建路径
        current_username = os.getlogin()
        # full_path = os.path.abspath(__file__)
        full_filename = os.path.basename(self.exe_path)
        filename, ext = os.path.splitext(full_filename)
        shortcut_location = f"C:\\Users\\{current_username}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{filename}.lnk"
        return shortcut_location

    def create_shortcut(self,shortcut_location):
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_location)
        shortcut.Targetpath = self.exe_path
        shortcut.save()

    def delete_shortcut(self,shortcut_location):
        if os.path.exists(shortcut_location):
            try:
                os.remove(shortcut_location)
            except Exception as e:
                print("删除文件失败",e)
        else:
            print("没有找到快捷方式")
    

class taskModel():
    name = None
    root_path = None
    pattern = "*"
    recursive = False
    days = 0
    size = 0
    number = 0
    trigger_args = None
    status = 0
    
    def __init__(self, name: str, root_path: str,pattern: str="*",recursive: bool=False,
                 days: int=0,size: int =0,number: int=0,trigger_args: str=None,status: int=0) -> None:
        self.name = name
        self.root_path = root_path
        self.pattern = pattern
        self.recursive = recursive
        self.days = days
        self.size = size
        self.number = number
        self.trigger_args = trigger_args
        self.status = status
    
    def task_data(self):
        task = {
            "name": self.name,
            "root_path": self.root_path,
            "pattern": self.pattern,
            "recursive": self.recursive,
            "days": self.days,
            "size": self.size,
            "number": self.number,
            "trigger_args": self.trigger_args,
            "status": self.status
            }
        
        return task
    

class taskManager():
    
    @classmethod
    def start_delete_task(cls,task,test: bool=False):
        file_delete  = FileDelete()
        file_delete.main(
            root_path=task.get("root_path"),
            pattern=task.get("pattern"),
            recursive=task.get("recursive"),
            days=task.get("days"),
            size=task.get("size"),
            test=test
        )
    
    @classmethod
    def start_delete_task_full(cls,index,test: bool=False):
        config_ins = ConfigManage()
        task = config_ins.get_config("tasks")[index]
        cls.start_delete_task(task,test)
    
    @classmethod
    def load_sched_job(cls):
        """加载任务到定时器"""
        sched_manage = ScheduleManage(SCHEDULER)
        config_manage = ConfigManage()
        tasks = config_manage.get_config("tasks")
        for index,task in enumerate(tasks):
            if task.get('status') == 1:
                if not sched_manage.job_exists(str(index)):
                    sched_manage.add_job(str(index),task['trigger_args'])
            elif task.get('status') == 2:
                if not sched_manage.job_exists(str(str(index))):
                    sched_manage.add_job(str(index),task['trigger_args'])
                sched_manage.pause_job(str(str(index)))


class ScheduleManage():
    def __init__(self, scheduler: BaseScheduler) -> None:
        self.scheduler = scheduler
    
    
    def str_schedule_task(self,job: Job):
        """定时任务格式化"""        
        next_run_time: time = job.next_run_time
        next_run_time = next_run_time.strftime("%Y-%m-%d %H:%M:%S") if next_run_time else None
        job_data = {
            "id": job.id,
            "next_run_time": next_run_time if next_run_time else ""
        }
        return job_data
        
    def get_schedule_tasks(self):
        jobs: list = self.scheduler.get_jobs()
        schedule_tasks: list = []
        tasks = ConfigManage().get_config("tasks")
        for job in jobs:
            schedule_task = self.str_schedule_task(job)
            id =  schedule_task.get('id')
            task: dict = tasks[int(id)]
            schedule_task['name'] = task.get("name")
            schedule_task['trigger_args'] = task.get("trigger_args")
            next_run_time = schedule_task.get('next_run_time')
            if next_run_time:
                schedule_task['status'] = "正在运行"
            else:
                schedule_task['status'] = "暂停"
            
            schedule_tasks.append(schedule_task)
        return schedule_tasks
    
    def add_job(self,id:str,trigger_args:str):
        
        trigger = self.parse_trigger("cron",trigger_args)
        if trigger is None:
            return
        self.scheduler.add_job(
            func=taskManager.start_delete_task_full,
            trigger=trigger,id=str(id),
            replace_existing=True,args=[id],coalesce=True
            )
    
    def parse_trigger(self, trigger, trigger_args):
        if trigger == 'interval':
            return IntervalTrigger(seconds=int(trigger_args))
        elif trigger == 'date':
            return DateTrigger(run_date=trigger_args)
        elif trigger == 'cron':
            trigger_args = trigger_args.strip()
            try:
                second,minute,hour,day, month, week = trigger_args.split()
                return CronTrigger(second=second,minute=minute, hour=hour, day=day, month=month, day_of_week=week)
            except ValueError:
                logger.error(f'定时参数有误:{trigger_args}')
                return None
            # return CronTrigger.from_crontab(trigger_args)
        else:
            raise TypeError(f'unknown schedule policy: {trigger!r}')
    
    def resume_job(self,id: str):
        job: Job = self.scheduler.get_job(job_id=str(id))
        job.resume()
    
    def pause_job(self,id: str):
        job: Job = self.scheduler.get_job(job_id=str(id))
        job.pause()
    
    def remove_job(self,id: str):
        job: Job = self.scheduler.get_job(job_id=str(id))
        job.remove()
    
    def job_exists(self, job_id: str):
        return job_id in self.scheduler.get_jobs()

class ConfigManage():
    def __init__(self, file: str=None) -> None:
        if not file:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            dir_path = os.path.dirname(exe_path)
            self.file = os.path.join(dir_path,'config.json')
        self.init_config()
            
    def init_config(self):
        if os.path.exists(self.file):
            return
        
        config = {
            "auto_start": False,
            "show_task_col": ["name","root_path","pattern","recursive","days","size","number","trigger_args","status"],
            "tasks": []
        }
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)

    
    def get_config(self, root_key: str=None):
        with open(self.file, 'r',encoding='utf-8') as f:
            config = json.load(f)
        
        if root_key:
            config = config.get(root_key)
        return config
    
    def add_task(self,task: taskModel):
        config: dict = self.get_config()
        tasks: list = config.get('tasks')
        task_data = task.task_data()
        tasks.append(task_data)
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
    
    def change_task(self,index,task: taskModel):
        config: dict = self.get_config()
        tasks: list = config.get('tasks')
        
        task_data = task.task_data()
        tasks[index] = task_data
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
    
    def del_task(self,index):
        config: dict = self.get_config()
        tasks: list = config.get('tasks') 
        del tasks[index]
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
    
    def load_task_data(self,index):
        config: dict = self.get_config()
        task: dict = config.get('tasks')[index]
        task_model = taskModel(**task)
        
        return task_model
    
    def change_task_status(self,index,status):
        config: dict = self.get_config()
        tasks: list = config.get('tasks') 
        task: dict = tasks[index]
        task['status'] = status
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
    
    def change_auto_start(self,status: bool=False):
        """修改开机自启状态"""
        config: dict = self.get_config()
        config['auto_start'] = status
        with open(self.file, 'w',encoding="utf-8") as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
    
    def get_auto_start(self):
        """获取开机自启状态"""
        config: dict = self.get_config()
        return config.get('auto_start',False)

class MinimizeToTray():
    """最小化到托盘"""
    
    def __init__(self, parent: QWidget) -> None:
        self.parent = parent
        ### 初始化系统托盘相关的对象和菜单项
        self._restore_action = QAction()
        self._quit_action = QAction()
        self._tray_icon_menu = QMenu()
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(QIcon(":/icon.ico"))  # 替换为你的图标路径
        self.tray_icon.setToolTip("文件定时删除工具")
        self.create_actions()
        self.create_tray_icon()
        self.tray_icon.show()
        # 连接系统托盘图标的激活事件
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
        
        ## 最小化到系统托盘
    def minimize_to_tray(self):
        self.parent.hide()

    def restore_from_tray(self):
        if self.parent.isMinimized():
            self.parent.showNormal()
        elif self.parent.isMaximized():
            self.parent.showMaximized()
        else:
           self.parent.show()

    def tray_icon_activated(self, reason):
        # 当系统托盘图标被点击时的处理
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # 如果点击的是触发事件（比如左键单击），则还原窗口
            self.restore_from_tray()

    def create_actions(self):
        # 创建菜单项
        self._restore_action = QAction("显示", self.parent)
        self._restore_action.triggered.connect(self.restore_from_tray)  # "显示"菜单项触发还原窗口的操作
        self._quit_action = QAction("退出", self.parent)
        self._quit_action.triggered.connect(QApplication.quit)  # "退出"菜单项触发退出应用程序的操作

    def create_tray_icon(self):
        # 创建系统托盘图标和上下文菜单
        self._tray_icon_menu = QMenu(self.parent)
        self._tray_icon_menu.addAction(self._restore_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._quit_action)
        self.tray_icon.setContextMenu(self._tray_icon_menu)
        self.tray_icon.show()
        
        
        
class MainWindows(QMainWindow):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.config_manage = ConfigManage()
        self.sched_manage  = ScheduleManage(SCHEDULER)
        
        self.select_row = None
        self.sched_select_row = None
        self.__ui = Ui_MainWindow()
        self.__ui.setupUi(self)
        self.setWindowIcon(QIcon(":/icon.ico"))
        ## 最小化到托盘
        self.minimize_Tray = MinimizeToTray(self)
        ## 任务列表tag
        self.show_tasks()
        self.__ui.task_horizontalLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.__ui.tabWidget.setCurrentIndex(0)
        self.__ui.addButton.clicked.connect(self.show_input_dialog)
        self.__ui.refreshButton.clicked.connect(self.show_tasks)
        # 根据内容自动调整列宽
        self.__ui.table_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__ui.table_list.itemSelectionChanged.connect(self.handleItemSelectionChanged)
        self.__ui.editButton.clicked.connect(self.change_task)
        self.__ui.delButton.clicked.connect(self.show_del_dialog)
        self.__ui.fmdButton.clicked.connect(self.show_start_dialog)
        self.__ui.fmdtButton.clicked.connect(lambda: self.show_start_dialog(test=True))
        self.__ui.startTaskButton.clicked.connect(self.start_schedule_task)
        # 开机启动配置
        self.__ui.autoStartCheckBox.setChecked(self.config_manage.get_auto_start())
        self.__ui.autoStartCheckBox.clicked.connect(self.auto_start)
        
        ## 定时任务tag
        self.__ui.sched_horizontalLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.__ui.tabWidget.currentChanged.connect(self.tag_change)
        # 表格
        self.__ui.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.__ui.sched_table.itemSelectionChanged.connect(self.sched_handleItemSelectionChanged)
        # 按钮
        self.__ui.sched_refreshButton.clicked.connect(self.show_schedule_table)
        self.__ui.sched_startButton.clicked.connect(self.start_sched_job)
        self.__ui.sched_stopButton.clicked.connect(self.stop_sched_job)
        self.__ui.sched_delButton.clicked.connect(self.remove_sched_job)
        
        ## 日志tag
        self.logger_conf()
        self.__ui.log_horizontalLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.__ui.log_clearButton.clicked.connect(self.clear_ui_log)
      
    
    def hideEvent(self, event):
        """最小化事件"""
        if self.isMinimized():
            self.minimize_Tray.minimize_to_tray()
      
    def tag_change(self):
         index = self.__ui.tabWidget.currentIndex()
         if index == 1:
             self.show_schedule_table()
    
    def logger_conf(self):
        log_edit = self.__ui.logEdit
        handler =  QTextEditHandler(log_edit)
        logger.addHandler(handler)
    
    def clear_ui_log(self):
        self.__ui.logEdit.clear()
    
    def show_tasks(self):
        table_list = self.__ui.table_list
        table_list.setRowCount(0)
        col_count = table_list.columnCount()
        
        config = self.config_manage.get_config()
        
        show_task_col = config.get("show_task_col")
        for index,task in enumerate(config['tasks']):
            table_list.insertRow(index)
            for col in range(col_count):
                text = str(task.get(show_task_col[col]))
                if show_task_col[col] == "recursive":
                    if text == "True":
                        text = "是"
                    elif text == "False":
                        text = "否"
                if show_task_col[col] == "status":
                    if  text == "1":
                        text = "运行中"
                    elif text == "2":
                        text = "暂停"
                    else:
                        text = "未启动"

                item = QTableWidgetItem(text)
                
                table_list.setItem(index, col, item)
    
    def show_input_dialog(self):
        # 弹出对话框  
        dialog = InputDialog(self)
        dialog.exec()
        self.show_tasks()
    
    def handleItemSelectionChanged(self):
        # 获取所有选中的项目
        items = self.__ui.table_list.selectedItems()
        if items:
            self.select_row = items[0].row()
    
    def change_task(self):
        if self.select_row is None:
            return
        dialog = InputDialog(self,mode="change",select_row=self.select_row)
        dialog.set_input_text(self.select_row)
        dialog.exec()
        self.show_tasks()
    
    def show_del_dialog(self):
        if self.select_row is None:
            return 
        
        tasks = self.config_manage.get_config("tasks")
        tasks_name = tasks[self.select_row]['name']
        result = QMessageBox.warning(self, '任务删除', f'是否确认删除"{tasks_name}"任务？', QMessageBox.StandardButton.No | QMessageBox.StandardButton.Ok)
        if result == QMessageBox.StandardButton.Ok:
            self.config_manage.del_task(self.select_row)
            self.show_tasks()
    
    def show_start_dialog(self,test: bool=False):
        if self.select_row is None:
            return 
        
        task = self.config_manage.get_config("tasks")[self.select_row]
        task_name = task['name']
        if test:
            result = QMessageBox.information(self, '删除任务启动测试', f'是否确认启动"{task_name}"任务？', QMessageBox.StandardButton.No | QMessageBox.StandardButton.Ok)
            if result == QMessageBox.StandardButton.Ok:
                taskManager().start_delete_task(task=task,test=True)
        else:
            result = QMessageBox.information(self, '删除任务启动', f'是否确认启动"{task_name}"任务？', QMessageBox.StandardButton.No | QMessageBox.StandardButton.Ok)
            if result == QMessageBox.StandardButton.Ok:
                taskManager().start_delete_task(task=task)
    
    def auto_start(self):
        """开机启动"""
        auto = AutoStart()
        if self.__ui.autoStartCheckBox.isChecked():
            auto.auto_start_on()
            self.config_manage.change_auto_start(True)
        else:
            auto.auto_start_off()
            self.config_manage.change_auto_start(False)
    
    def start_schedule_task(self):
        """启动定时删除任务"""
        if self.select_row is None:
            return 
        
        config_ins = self.config_manage
        task = config_ins.get_config("tasks")[self.select_row]
        task_name = task['name']
        task_trigger = task['trigger_args']
        result = QMessageBox.warning(self, '启动定时删除任务', f'是否确认启动"{task_name}"定时删除任务？', QMessageBox.StandardButton.No | QMessageBox.StandardButton.Ok)
        
        if result == QMessageBox.StandardButton.Ok:
            self.sched_manage.add_job(self.select_row,task_trigger)
            self.show_schedule_table()
            self.config_manage.change_task_status(self.select_row,1)
    
    def show_schedule_table(self):
        table_list = self.__ui.sched_table
        table_list.setRowCount(0)
        col_count = table_list.columnCount()
        sched_tasks = self.sched_manage.get_schedule_tasks()
        
        show_task_col = ["name","trigger_args", "status", "next_run_time"]
        for index,task in enumerate(sched_tasks):
            table_list.insertRow(index)
            for col in range(col_count):
                text = str(task.get(show_task_col[col]))
                item = QTableWidgetItem(text)
                table_list.setItem(index, col, item)
    
    def sched_handleItemSelectionChanged(self):
        """定时器表格选中行改变事件
        """
        items = self.__ui.sched_table.selectedItems()
        if items:
            self.sched_select_row = items[0].row()
            
    def start_sched_job(self):
        if self.sched_select_row is None:
            return
        sched_task = self.sched_manage.get_schedule_tasks()[self.sched_select_row]
        
        self.sched_manage.resume_job(str(sched_task.get('id')))
        self.config_manage.change_task_status(int(sched_task.get('id')),1)
        self.show_schedule_table()
        self.show_tasks()
    
    def stop_sched_job(self):
        if self.sched_select_row is None:
            return
        sched_task = self.sched_manage.get_schedule_tasks()[self.sched_select_row]
        self.sched_manage.pause_job(str(sched_task.get('id')))
        self.config_manage.change_task_status(int(sched_task.get('id')),2)
        self.show_schedule_table()
        self.show_tasks()
    
    def remove_sched_job(self):
        if self.sched_select_row is None:
            return
        sched_task = self.sched_manage.get_schedule_tasks()[self.sched_select_row]
        self.sched_manage.remove_job(str(sched_task.get('id')))
        self.config_manage.change_task_status(int(sched_task.get('id')),0)
        self.show_schedule_table()
        self.show_tasks()
    
    

class InputDialog(QDialog):  
    def __init__(self,parent=None,mode: str="add",select_row: int=None) -> None:
        super().__init__(parent)
        self.config_manage = ConfigManage()
        
        self.__ui = Ui_InputDialog()
        self.__ui.setupUi(self)
        self.select_row = select_row
        if mode == "add":
            self.setWindowTitle('任务添加')
            self.__ui.okButton.clicked.connect(self.add_task)
        else:
            self.setWindowTitle('任务编辑')
            self.__ui.okButton.clicked.connect(self.change_task)
        
        self.__ui.okButton.clicked.connect(self.close)
        self.__ui.cancelButton.clicked.connect(self.close)
        self.__ui.fileSelectButton.clicked.connect(self.file_select)
    
    def set_input_text(self,index):
        task = self.config_manage.load_task_data(index)
        
        self.__ui.nameEdit.setText(task.name)
        self.__ui.pathEdit.setText(task.root_path)
        self.__ui.patternEdit.setText(task.pattern)
        self.__ui.yes_recursiveRadioButton.setChecked(task.recursive)
        self.__ui.day_spinBox.setValue(task.days)
        self.__ui.size_spinBox.setValue(task.size)
        self.__ui.number_spinBox.setValue(task.number)
        self.__ui.timeEdit.setText(task.trigger_args)
    
    
    def get_input_text(self):
        name = self.__ui.nameEdit.text()
        root_path = self.__ui.pathEdit.text()
        pattern = self.__ui.patternEdit.text()
        recursive = self.__ui.yes_recursiveRadioButton.isChecked()
        day = self.__ui.day_spinBox.value()
        size = self.__ui.size_spinBox.value()
        number = self.__ui.number_spinBox.value()
        trigger_args = self.__ui.timeEdit.text()
        
        task = taskModel(name,root_path,pattern,recursive,day,size,number,trigger_args)
        return task
    
    def add_task(self):
        task = self.get_input_text()
        
        self.config_manage.add_task(task)
    
    def change_task(self):
        if self.select_row is None:
            return
        
        task = self.get_input_text()
        self.config_manage.change_task(self.select_row,task)
    
    def file_select(self):
        fd = QFileDialog()
        file_path = fd.getExistingDirectory()
        if file_path:
            self.__ui.pathEdit.setText(file_path)

def error_handler(exc_type, exc_value, exc_tb):
    """崩溃弹窗"""
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    reply = QMessageBox.critical(
        None, 'Error Caught!:', error_message,
        QMessageBox.StandardButton.Abort | QMessageBox.StandardButton.Retry,
        QMessageBox.StandardButton.Abort)
    if reply == QMessageBox.StandardButton.Abort:
        sys.exit(1)
    
    
if __name__ == '__main__':
    sys.excepthook = error_handler
    logger = init_logger()
    SCHEDULER = BackgroundScheduler(timezone='Asia/Shanghai')
    SCHEDULER.start()
    taskManager.load_sched_job()
    app = QApplication(sys.argv)
    window = MainWindows()
    window.show()
    sys.exit(app.exec())