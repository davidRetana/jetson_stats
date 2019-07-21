# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import abc
import curses
# Graphics elements
from .jtopguilib import (check_size,
                         check_curses)
# Initialization abstract class
# In according with: https://gist.github.com/alanjcastonguay/25e4db0edd3534ab732d6ff615ca9fc1
ABC = abc.ABCMeta('ABC', (object,), {})


class Page(ABC):

    def __init__(self, name, stdscr, jetson, refresh):
        self.name = name
        self.stdscr = stdscr
        self.jetson = jetson
        self.refresh = refresh

    @abc.abstractmethod
    @check_curses
    def draw(self, key):
        pass

    def keyboard(self, key):
        pass


class JTOPGUI:
    """
        The easiest way to use curses is to use a wrapper around a main function
        Essentially, what goes in the main function is the body of your program,
        The `stdscr' parameter passed to it is the curses screen generated by our
        wrapper.
    """
    COLORS = {"RED": 1, "GREEN": 2, "YELLOW": 3, "BLUE": 4, "MAGENTA": 5, "CYAN": 6}

    def __init__(self, stdscr, refresh, jetson, pages, init_page=0, start=True):
        # Define pairing colors
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # Set curses reference, refresh and jetson controller
        self.stdscr = stdscr
        self.refresh = refresh
        self.jetson = jetson
        # Initialize all Object pages
        self.pages = [obj(stdscr, jetson, refresh) for obj in pages]
        # Set default page
        self.n_page = 0
        self.set(init_page)
        # Initialize keyboard status
        self.key = -1
        self.old_key = -1
        # Run the GUI
        if start:
            self.run()

    def run(self):
        # In this program, we don't want keystrokes echoed to the console,
        # so we run this to disable that
        curses.noecho()
        # Additionally, we want to make it so that the user does not have to press
        # enter to send keys to our program, so here is how we get keys instantly
        curses.cbreak()
        # Hide the cursor
        curses.curs_set(0)
        # Lastly, keys such as the arrow keys are sent as funny escape sequences to
        # our program. We can make curses give us nicer values (such as curses.KEY_LEFT)
        # so it is easier on us.
        self.stdscr.keypad(True)
        # Refreshing page curses loop
        # https://stackoverflow.com/questions/54409978/python-curses-refreshing-text-with-a-loop
        self.stdscr.nodelay(1)
        """ Here is the loop of our program, we keep clearing and redrawing in this loop """
        while self.keyboard():
            # Draw pages
            self.draw()

    @check_size(20, 50)
    def draw(self):
        # First, clear the screen
        self.stdscr.erase()
        # Write head of the jtop
        self.header()
        # Get page selected
        page = self.pages[self.n_page]
        # Draw the page
        page.draw(self.key)
        # Draw menu
        self.menu()
        # Draw the screen
        self.stdscr.refresh()
        # Set a timeout and read keystroke
        self.stdscr.timeout(self.refresh)

    def increase(self):
        idx = self.n_page + 1
        self.set(idx + 1)

    def decrease(self):
        idx = self.n_page + 1
        self.set(idx - 1)

    def set(self, idx):
        if idx <= len(self.pages) and idx > 0:
            self.n_page = idx - 1

    @check_curses
    def header(self):
        board = self.jetson.board["board"]
        board_info = board["Name"] + " - Jetpack " + board["Jetpack"]
        self.stdscr.addstr(0, 0, board_info, curses.A_BOLD)
        if self.jetson.userid != 0:
            self.stdscr.addstr(0, len(board_info) + 1, "- PLEASE RUN WITH SUDO", curses.color_pair(1))

    @check_curses
    def menu(self):
        height, width = self.stdscr.getmaxyx()
        # Set background for all menu line
        self.stdscr.addstr(height - 1, 0, ("{0:<" + str(width - 1) + "}").format(" "), curses.A_REVERSE)
        position = 1
        for idx, page in enumerate(self.pages):
            if self.n_page != idx:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=page.name), curses.A_REVERSE)
            else:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=page.name))
            position += len(page.name) + 2
            self.stdscr.addstr(height - 1, position, " - ", curses.A_REVERSE)
            position += 3
        # Add close option menu
        self.stdscr.addstr(height - 1, position, "Q to close", curses.A_REVERSE)
        # Author name
        name_author = "Raffaello Bonghi"
        self.stdscr.addstr(height - 1, width - len(name_author), name_author, curses.A_REVERSE)

    def keyboard(self):
        self.key = self.stdscr.getch()
        if self.old_key != self.key:
            # keyboard check list
            if self.key == curses.KEY_LEFT:
                self.decrease()
            elif self.key == curses.KEY_RIGHT:
                self.increase()
            elif self.key in [ord(str(n)) for n in range(10)]:
                num = int(chr(self.key))
                self.set(num)
            elif self.key == ord('q') or self.key == ord('Q'):
                # keyboard check quit button
                return False
            else:
                # Run extra control for page if exist
                for page in self.pages:
                    # Run key controller
                    page.keyboard(self.key)
            # Store old value key
            self.old_key = self.key
        return True
# EOF
