"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""

import logging
import unittest
from multiprocessing import Process
from string import join

import os
from pysol_base.FileUtility import FileUtility
from pysol_base.SolBase import SolBase

from pysol_daemon_test.Daemon.CustomDaemon import CustomDaemon

SolBase.voodoo_init()
logger = logging.getLogger(__name__)
SolBase.fix_paths_for_popen()


class TestDaemon(unittest.TestCase):
    """
    Test
    """

    def setUp(self):
        """
        Setup
        """
        SolBase.voodoo_init()
        self.run_idx = 0

        # Log
        logger.info("Entering, %s", SolBase.get_current_pid_as_string())

        # Config
        self.test_timeout_ms = 5000
        self.stdout_timeout_ms = 5000
        self.std_err_timeout_ms = 500

        self.daemon_pid_file = "/tmp/Daemon.pid"

        self.daemon_std_out = "/tmp/Daemon.out.txt"
        self.daemon_std_err = "/tmp/Daemon.err.txt"

        # Clean
        self._clean_files()

    def tearDown(self):
        """
        Test
        """
        pass

    # ==============================
    # UTILITIES
    # ==============================

    def _clean_files(self):
        """
        Clean files
        """

        if FileUtility.is_file_exist(self.daemon_pid_file):
            logger.debug("Deleting %s", self.daemon_pid_file)
            os.remove(self.daemon_pid_file)

        if FileUtility.is_file_exist(self.daemon_std_out):
            logger.debug("Deleting %s", self.daemon_std_out)
            os.remove(self.daemon_std_out)

        if FileUtility.is_file_exist(self.daemon_std_err):
            logger.debug("Deleting %s", self.daemon_std_err)
            os.remove(self.daemon_std_err)

        if FileUtility.is_file_exist(CustomDaemon.DAEMON_LAST_ACTION_FILE):
            logger.debug("Deleting %s", CustomDaemon.DAEMON_LAST_ACTION_FILE)
            os.remove(CustomDaemon.DAEMON_LAST_ACTION_FILE)

    def _reset_std_capture(self):
        pass

    def _file_to_list(self, file_name, sep="\n"):
        """
        Load a file to a list, \n delimited
        :param file_name: File name
        :type file_name: str
        :param sep: separator
        :type sep: str
        :return list
        :rtype list
        """

        ret = None
        # noinspection PyBroadException
        try:
            if FileUtility.is_file_exist(file_name):
                ret = FileUtility.file_to_textbuffer(file_name, "ascii")
        except:
            ret = None
        finally:
            if SolBase.is_string_not_empty(ret):
                return ret.split(sep)
            else:
                return list()

    def _status_to_dict(self, file_name, sep="\n", value_sep="="):
        """
        Status to dict
        :param file_name: File name
        :type file_name: str
        :param sep: separator
        :type sep: str
        :param sep: separator for value
        :type sep: str
        :return dict
        :rtype dict
        """

        out_dic = dict()
        cur_list = self._file_to_list(file_name, sep)
        for it in cur_list:
            ar = it.split(value_sep)
            if len(ar) != 2:
                continue
            out_dic[ar[0]] = ar[1]

        return out_dic

    def _get_std_out(self):
        """
        Get
        :return: A String
        """

        ms_start = SolBase.mscurrent()
        while True:
            ar = self._file_to_list(self.daemon_std_out)
            if len(ar) > 0:
                return ar
            elif SolBase.msdiff(ms_start) > self.stdout_timeout_ms:
                return list()
            else:
                SolBase.sleep(10)

    def _get_std_err(self):
        """
        Get
        :return: A String
        """

        ms_start = SolBase.mscurrent()
        while True:
            ar = self._file_to_list(self.daemon_std_err)
            if len(ar) > 0:
                return ar
            elif SolBase.msdiff(ms_start) > self.std_err_timeout_ms:
                return list()
            else:
                SolBase.sleep(10)

    def test_start_status_reload_stop(self):
        """
        Test
        """

        try:
            # Start
            self._reset_std_capture()

            # Params
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("-stderr={0}".format(self.daemon_std_err))
            ar.append("-stdout={0}".format(self.daemon_std_out))
            ar.append("start")

            # =========================
            # START
            # =========================

            # Launch
            logger.info("Start, ar=%s", ar)
            p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
            p.start()
            p.join(self.test_timeout_ms)

            # Try wait for stdout
            logger.info("Wait")
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0:
                    logger.info("Wait break")
                    break
                else:
                    SolBase.sleep(10)

            # Get std (caution, we are async since forked)
            logger.info("Get")
            logger.info("stdOut ### START")
            for s in self._get_std_out():
                logger.info("stdOut => %s", s)
            logger.info("stdOut ### END")

            logger.info("stdErr ### START")
            for s in self._get_std_err():
                logger.info("stdErr => %s", s)
            logger.info("stdErr ### END")

            # Check
            logger.info("Check")
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue(len(self._get_std_out()) > 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" ERROR ") < 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" WARN ") < 0)

            # =========================
            # STATUS
            # =========================

            for _ in range(0, 10):
                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("status")

                # Launch
                p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
                p.start()
                p.join(self.test_timeout_ms)
                self.assertTrue(p.exitcode == 0)

            # =========================
            # RELOAD
            # =========================

            for _ in range(0, 10):
                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("reload")

                # Launch
                p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
                p.start()
                p.join(self.test_timeout_ms)
                self.assertTrue(p.exitcode == 0)

            # =========================
            # STOP
            # =========================

            # Args
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("stop")

            # Launch
            p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
            p.start()
            p.join(self.test_timeout_ms)

            # =========================
            # OVER, CHECK LOGS
            # =========================

            # Try wait for stdout
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_stop") >= 0 and join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_status") >= 0:
                    break
                else:
                    SolBase.sleep(10)

            # Get std (caution, we are async since forked)
            logger.info("stdOut ### START")
            for s in self._get_std_out():
                logger.info("stdOut => %s", s)
            logger.info("stdOut ### END")

            logger.info("stdErr ### START")
            for s in self._get_std_err():
                logger.info("stdErr => %s", s)
            logger.info("stdErr ### END")

            # Check
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue(len(self._get_std_out()) > 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" ERROR ") < 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_stop") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_status") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" WARN ") < 0)

            # =========================
            # OVER, CHECK ACTION FILE
            # =========================
            buf = FileUtility.file_to_textbuffer(CustomDaemon.DAEMON_LAST_ACTION_FILE, "ascii")
            self.assertTrue(buf.find("is_running=False") >= 0)
            self.assertTrue(buf.find("start_count=1") >= 0)
            self.assertTrue(buf.find("stop_count=1") >= 0)
            self.assertTrue(buf.find("status_count=10") >= 0)
            self.assertTrue(buf.find("reload_count=10") >= 0)
            self.assertTrue(buf.find("last_action=stop") >= 0)
            self.assertTrue(buf.find("start_loop_exited=True") >= 0)

        finally:
            logger.debug("Exiting test, idx=%s", self.run_idx)

    def test_start_status_reload_stop_logfile(self):
        """
        Test
        """

        try:
            # Start
            self._reset_std_capture()

            # Params
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("-stderr={0}".format(self.daemon_std_err))
            ar.append("-stdout=/dev/null")
            ar.append("-logfile={0}".format(self.daemon_std_out))
            ar.append("start")

            # =========================
            # START
            # =========================

            # Launch
            p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
            p.start()
            p.join(self.test_timeout_ms)

            # Try wait for stdout
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0:
                    break
                else:
                    SolBase.sleep(10)

            # Get std (caution, we are async since forked)
            logger.info("stdOut ### START")
            for s in self._get_std_out():
                logger.info("stdOut => %s", s)
            logger.info("stdOut ### END")

            logger.info("stdErr ### START")
            for s in self._get_std_err():
                logger.info("stdErr => %s", s)
            logger.info("stdErr ### END")

            # Check
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue(len(self._get_std_out()) > 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" ERROR ") < 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" WARN ") < 0)

            # =========================
            # STATUS
            # =========================

            for _ in range(0, 10):
                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("status")

                # Launch
                p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
                p.start()
                p.join(self.test_timeout_ms)
                self.assertTrue(p.exitcode == 0)

            # =========================
            # RELOAD
            # =========================

            for _ in range(0, 10):
                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("reload")

                # Launch
                p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
                p.start()
                p.join(self.test_timeout_ms)
                self.assertTrue(p.exitcode == 0)

            # =========================
            # STOP
            # =========================

            # Args
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("stop")

            # Launch
            p = Process(target=CustomDaemon.main_helper, args=(ar, {}))
            p.start()
            p.join(self.test_timeout_ms)

            # =========================
            # OVER, CHECK LOGS
            # =========================

            # Try wait for stdout
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_stop") >= 0 \
                        and join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_status") >= 0:
                    break
                else:
                    SolBase.sleep(10)

            # Get std (caution, we are async since forked)
            logger.info("stdOut ### START")
            for s in self._get_std_out():
                logger.info("stdOut => %s", s)
            logger.info("stdOut ### END")

            logger.info("stdErr ### START")
            for s in self._get_std_err():
                logger.info("stdErr => %s", s)
            logger.info("stdErr ### END")

            # Check
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue(len(self._get_std_out()) > 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" ERROR ") < 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_start") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_stop") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" INFO | CustomDaemon@_on_status") >= 0)
            self.assertTrue(join(self._get_std_out(), '\n').find(" WARN ") < 0)

            # =========================
            # OVER, CHECK ACTION FILE
            # =========================
            buf = FileUtility.file_to_textbuffer(CustomDaemon.DAEMON_LAST_ACTION_FILE, "ascii")
            self.assertTrue(buf.find("is_running=False") >= 0)
            self.assertTrue(buf.find("start_count=1") >= 0)
            self.assertTrue(buf.find("stop_count=1") >= 0)
            self.assertTrue(buf.find("status_count=10") >= 0)
            self.assertTrue(buf.find("reload_count=10") >= 0)
            self.assertTrue(buf.find("last_action=stop") >= 0)
            self.assertTrue(buf.find("start_loop_exited=True") >= 0)

        finally:
            logger.debug("Exiting test, idx=%s", self.run_idx)
