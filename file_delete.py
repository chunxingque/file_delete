#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
from typing import Tuple
from datetime import datetime
import logging

logger = logging.getLogger('logger')

class FileDelete():
    """文件删除类"""
    def main(self,root_path: str, pattern: str, recursive: bool=False, days: int=None,size: int=None,number: int=0,empty_dir: bool=False,test: bool=False):
        if number:
            self.delete_files_number(root_path, pattern,number,days,test)
        else:
            self.delete_files(root_path, pattern,recursive,days,size,empty_dir,test)
    
    def get_number_files(self,files: list, number: int) -> Tuple[list,list]:
        """查找最新的number个文件

        Args:
            files (list): 文件路径列表
            number (int): _description_

        Returns:
            _type_: _description_
        """
        sort_files = sorted(files, 
                            key=lambda x: datetime.fromtimestamp(os.path.getmtime(x)),reverse=False)
        
        files_size = len(sort_files)
        num_new_files = []
        num_old_files = []
        if number < files_size:
            num_new_files = sort_files[files_size-number:]
            num_old_files = sort_files[:files_size-number]
            return num_new_files,num_old_files
        else:
            num_new_files = sort_files
            return num_new_files,num_old_files

    def get_days_files(self,files: list, days: int ) ->list:
        """查找days天前的文件

        Args:
            files (list): 文件路径列表
            days (int): 天数

        Returns:
            list: days天前的文件
        """
        old_days_files = []
        for file in files:
            if os.path.isfile(file):
                mod_time = datetime.fromtimestamp(os.path.getmtime(file))
                if (datetime.now() - mod_time).days > days:
                    old_days_files.append(file)
        return old_days_files

    def delete_files_number(self,dir_path: str, pattern: str, number: int=None,days: int=None,test: bool=False):
        """批量文件删除，支持保留数量, 名称匹配，日期匹配,不支持递归

        Args:
            dir_path (str): 目录路径
            pattern (str): 文件名匹配规则
            number (int, optional): 保留数量. Defaults to None.
            days (int, optional): 天数. Defaults to None.
            recursive (bool, optional): 是否递归. Defaults to False.
        """
        pattern_files = glob.glob(pathname=os.path.join(dir_path,pattern),recursive=False)
        if number and days:
            num_new_files,num_old_files = self.get_number_files(pattern_files,number)
            old_days_files = self.get_days_files(pattern_files,days)
            del_files= set(old_days_files).difference(num_new_files)
        elif number:
            num_new_files,num_old_files = self.get_number_files(pattern_files,number)
            del_files = num_old_files
        elif days:
            del_files = self.get_days_files(pattern_files,days)
        else:
            del_files = pattern_files
        
        if del_files:
            for file in del_files:
                if os.path.isfile(file) and not test:
                    os.remove(file)
                    logger.info("delete: %s",file)
                else:
                    logger.info("delete test: %s",file)
        else:
            logger.info("没有匹配到文件")
    
    
    def delete_files(self,root_path: str, pattern: str, recursive: bool=False, days: int=None,size: int=None,empty_dir: bool=False,test: bool=False):
        """批量文件删除，支持名称匹配，日期匹配，递归子目录匹配

        Args:
            root_path (str): 匹配目录
            pattern (str): 匹配的名称

        Returns:
            list: 文件绝对路径的列表
        """
        files = glob.iglob(pathname=pattern,root_dir=root_path,recursive=recursive)  # 返回相对路径
        for file in files:
            file_path = os.path.join(root_path,file)
            if os.path.isfile(file_path):
                if days:            
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (datetime.now() - mod_time).days <= days:
                        continue
                if size:
                    if os.path.getsize(file_path) < size * 1024 * 1024:
                        continue
                
                if not test:
                    os.remove(file_path)
                    logger.info("delete: %s",file_path)
                else:
                    logger.info("delete test: %s",file_path)
            elif not os.listdir(file_path) and empty_dir:
                if not test:
                    os.rmdir(file_path)
                    logger.info("Deleted empty directory: %s", file_path)
                else:
                    logger.info("Deleted empty directory test: %s",file_path)

