# Copyright (C) 2019 Kataiser & https://github.com/Kataiser/tf2-rich-presence/contributors
# https://github.com/Kataiser/tf2-rich-presence/blob/master/LICENSE
# cython: language_level=3

import atexit
import functools
import gc
import json
import os
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
import traceback
import webbrowser
import winreg
from tkinter import messagebox
from typing import Union

import launcher
import localization
import logger
import utils


class GUI(tk.Frame):
    def __init__(self, master, log=None):
        if log:
            self.log = log
        else:
            self.log = logger.Log()
            self.log.to_stderr = True

        self.log.info(f"Opening settings menu for TF2 Rich Presence {launcher.VERSION}")
        self.loc = localization.Localizer(self.log, get('language'))

        tk.Frame.__init__(self, master)
        self.master = master
        check_int_command = self.register(check_int)
        atexit.register(self.window_close_log)

        master.title(self.loc.text("TF2 Rich Presence ({0}) settings").format(launcher.VERSION))
        master.resizable(0, 0)  # disables resizing

        # set window icon, doesn't work if launching from Pycharm for some reason
        try:
            master.iconbitmap(default='tf2_logo_blurple_wrench.ico')
        except tk.TclError:
            master.iconbitmap(default=os.path.join('resources', 'tf2_logo_blurple_wrench.ico'))

        self.log_levels = ['Debug', 'Info', 'Error', 'Critical', 'Off']
        self.sentry_levels = ['All errors', 'Crashes', 'Never']
        self.class_pic_types = ['Icon', 'Emblem', 'Portrait', 'None, use TF2 logo']
        # self.languages = ['English', 'German', 'French', 'Spanish', 'Portuguese', 'Italian', 'Dutch', 'Polish', 'Russian', 'Korean', 'Chinese', 'Japanese']
        self.languages = ['English', 'German', 'French', 'Spanish', 'Portuguese', 'Italian', 'Dutch', 'Polish']

        self.log_levels_display = [self.loc.text(item) for item in self.log_levels]
        self.sentry_levels_display = [self.loc.text(item) for item in self.sentry_levels]
        self.class_pic_types_display = [self.loc.text(item) for item in self.class_pic_types]
        # self.languages_display = ['English', 'Deutsch', 'Français', 'Español', 'Português', 'Italiano', 'Nederlands', 'Polski', 'русский язык', '한국어', '汉语', '日本語']
        self.languages_display = ['English', 'Deutsch', 'Français', 'Español', 'Português', 'Italiano', 'Nederlands', 'Polski']

        # create every setting variable without values
        self.sentry_level = tk.StringVar()
        self.wait_time = tk.IntVar()
        self.map_invalidation_hours = tk.IntVar()
        self.check_updates = tk.BooleanVar()
        self.request_timeout = tk.IntVar()
        self.hide_queued_gamemode = tk.BooleanVar()
        self.log_level = tk.StringVar()
        self.console_scan_kb = tk.IntVar()
        self.class_pic_type = tk.StringVar()
        self.language = tk.StringVar()
        self.map_time = tk.BooleanVar()
        self.trim_console_log = tk.BooleanVar()

        try:
            # load settings from registry
            self.settings_loaded = access_registry()
            self.log.debug(f"Current settings: {self.settings_loaded}")
            self.log.debug(f"Are default: {self.settings_loaded == get_setting_default(return_all=True)}")

            self.sentry_level.set(self.settings_loaded['sentry_level'])
            self.wait_time.set(self.settings_loaded['wait_time'])
            self.map_invalidation_hours.set(self.settings_loaded['map_invalidation_hours'])
            self.check_updates.set(self.settings_loaded['check_updates'])
            self.request_timeout.set(self.settings_loaded['request_timeout'])
            self.hide_queued_gamemode.set(self.settings_loaded['hide_queued_gamemode'])
            self.log_level.set(self.settings_loaded['log_level'])
            self.console_scan_kb.set(self.settings_loaded['console_scan_kb'])
            self.class_pic_type.set(self.settings_loaded['class_pic_type'])
            self.language.set(self.settings_loaded['language'])
            self.map_time.set(self.settings_loaded['map_time'])
            self.trim_console_log.set(self.settings_loaded['trim_console_log'])
        except Exception:
            # probably a json decode error
            formatted_exception = traceback.format_exc()
            self.log.error(f"Error in loading settings, defaulting: \n{formatted_exception}")
            messagebox.showerror(self.loc.text("Error"), self.loc.text("Couldn't load settings, reverting to defaults.{0}").format(f'\n\n{formatted_exception}'))

            self.restore_defaults()
            self.settings_loaded = get_setting_default(return_all=True)

        # make options account for localization
        self.log_level.set(self.log_levels_display[self.log_levels.index(self.log_level.get())])
        self.sentry_level.set(self.sentry_levels_display[self.sentry_levels.index(self.sentry_level.get())])
        self.class_pic_type.set(self.class_pic_types_display[self.class_pic_types.index(self.class_pic_type.get())])
        self.language.set(self.languages_display[self.languages.index(self.language.get())])

        # create label frames
        lf_main = ttk.Labelframe(master, text=self.loc.text("Main"))
        lf_advanced = ttk.Labelframe(master, text=self.loc.text("Advanced"))

        # create settings widgets
        setting1_frame = ttk.Frame(lf_advanced)
        setting1_text = ttk.Label(setting1_frame, text="{}".format(
            self.loc.text("Log reporting frequency: ")))
        setting1_radiobuttons = []
        for sentry_level_text in self.sentry_levels_display:
            setting1_radiobuttons.append(ttk.Radiobutton(setting1_frame, variable=self.sentry_level, text=sentry_level_text, value=sentry_level_text, command=self.update_default_button_state))
        setting3_frame = ttk.Frame(lf_main)
        setting3_text = ttk.Label(setting3_frame, text="{}".format(
            self.loc.text("Delay between refreshes, in seconds: ")))
        setting3_option = ttk.Spinbox(setting3_frame, textvariable=self.wait_time, width=6, from_=0, to=1000, validate='all', validatecommand=(check_int_command, '%P', 1000),
                                      command=self.update_default_button_state)
        setting4_frame = ttk.Frame(lf_advanced)
        setting4_text = ttk.Label(setting4_frame, text="{}".format(
            self.loc.text("Hours before re-checking custom map gamemode: ")))
        setting4_option = ttk.Spinbox(setting4_frame, textvariable=self.map_invalidation_hours, width=6, from_=0, to=1000, validate='all', validatecommand=(check_int_command, '%P', 1000),
                                      command=self.update_default_button_state)
        setting5 = ttk.Checkbutton(lf_main, variable=self.check_updates, command=self.update_default_button_state, text="{}".format(
            self.loc.text("Check for program updates when launching")))
        setting6_frame = ttk.Frame(lf_advanced)
        setting6_text = ttk.Label(setting6_frame, text="{}".format(
            self.loc.text("Internet connection timeout (for updater and custom maps), in seconds: ")))
        setting6_option = ttk.Spinbox(setting6_frame, textvariable=self.request_timeout, width=6, from_=0, to=60, validate='all', validatecommand=(check_int_command, '%P', 60),
                                      command=self.update_default_button_state)
        setting8 = ttk.Checkbutton(lf_main, variable=self.hide_queued_gamemode, command=self.update_default_button_state, text="{}".format(
            self.loc.text("Hide game type (Casual, Comp, MvM) queued for")))
        setting9_frame = ttk.Frame(lf_advanced)
        setting9_text = ttk.Label(setting9_frame, text="{}".format(
            self.loc.text("Max log level: ")))
        setting9_radiobuttons = []
        for log_level_text in self.log_levels_display:
            setting9_radiobuttons.append(ttk.Radiobutton(setting9_frame, variable=self.log_level, text=log_level_text, value=log_level_text, command=self.update_default_button_state))
        setting10_frame = ttk.Frame(lf_advanced)
        setting10_text = ttk.Label(setting10_frame, text="{}".format(
            self.loc.text("Max kilobytes of console.log to scan: ")))
        setting10_option = ttk.Spinbox(setting10_frame, textvariable=self.console_scan_kb, width=8, from_=0, to=float('inf'), validate='all',
                                       validatecommand=(check_int_command, '%P', float('inf')), command=self.update_default_button_state)
        setting12_frame = ttk.Frame(lf_main)
        setting12_text = ttk.Label(setting12_frame, text="{}".format(
            self.loc.text("Selected class small image type: ")))
        setting12_radiobuttons = []
        for class_pic_type_text in self.class_pic_types_display:
            setting12_radiobuttons.append(ttk.Radiobutton(setting12_frame, variable=self.class_pic_type, text=class_pic_type_text, value=class_pic_type_text,
                                                          command=self.update_default_button_state))
        setting13_frame = ttk.Frame(lf_main)
        setting13_text = ttk.Label(setting13_frame, text="{}".format(
            self.loc.text("Language: ")))
        actual_language = self.language.get()
        setting13_options = ttk.OptionMenu(setting13_frame, self.language, self.languages[0], *self.languages_display, command=self.update_default_button_state)
        self.language.set(actual_language)
        setting14 = ttk.Checkbutton(lf_main, variable=self.map_time, command=self.update_default_button_state, text="{}".format(
            self.loc.text("Show time on current map instead of selected class")))
        setting15 = ttk.Checkbutton(lf_advanced, variable=self.trim_console_log, command=self.update_default_button_state, text="{}".format(
            self.loc.text("Limit console.log's size occasionally")))

        # download page button, but only if a new version is available
        db = utils.access_db()
        if db['available_version']['exists']:
            new_version_name = db['available_version']['tag']
            self.new_version_url = db['available_version']['url']

            self.update_button_text = tk.StringVar(value=self.loc.text(" Open {0} download page in default browser ").format(new_version_name))
            self.update_button = ttk.Button(lf_main, textvariable=self.update_button_text, command=self.open_update_page)
            self.update_button.grid(row=10, sticky=tk.W, padx=(20, 40), pady=(0, 12))

        # add widgets to the labelframes or main window
        setting1_frame.grid(row=12, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(4, 0))
        setting1_text.pack(side='left', fill=None, expand=False)
        for setting1_radiobutton in setting1_radiobuttons:
            setting1_radiobutton.pack(side='left', fill=None, expand=False)
        setting3_text.pack(side='left', fill=None, expand=False)
        setting3_option.pack(side='left', fill=None, expand=False)
        setting3_frame.grid(row=1, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(3, 0))
        setting4_text.pack(side='left', fill=None, expand=False)
        setting4_option.pack(side='left', fill=None, expand=False)
        setting4_frame.grid(row=10, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(4, 0))
        setting5.grid(row=9, sticky=tk.W, columnspan=2, padx=(20, 40), pady=(4, 10))
        setting6_text.pack(side='left', fill=None, expand=False)
        setting6_option.pack(side='left', fill=None, expand=False)
        setting6_frame.grid(row=11, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(4, 0))
        setting8.grid(row=6, sticky=tk.W, columnspan=2, padx=(20, 40), pady=(4, 0))
        setting9_text.pack(side='left', fill=None, expand=False)
        for setting9_radiobutton in setting9_radiobuttons:
            setting9_radiobutton.pack(side='left', fill=None, expand=False)
        setting9_frame.grid(row=13, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(4, 10))
        setting10_text.pack(side='left', fill=None, expand=False)
        setting10_option.pack(side='left', fill=None, expand=False)
        setting10_frame.grid(row=5, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(11, 0))
        setting12_text.pack(side='left', fill=None, expand=False)
        for setting12_radiobutton in setting12_radiobuttons:
            setting12_radiobutton.pack(side='left', fill=None, expand=False)
        setting12_frame.grid(row=8, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(4, 0))
        setting13_text.pack(side='left', fill=None, expand=False)
        setting13_options.pack(side='left', fill=None, expand=False)
        setting13_frame.grid(row=0, columnspan=2, sticky=tk.W, padx=(20, 40), pady=(9, 0))
        setting14.grid(row=2, sticky=tk.W, columnspan=2, padx=(20, 40), pady=(4, 0))
        setting15.grid(row=6, sticky=tk.W, columnspan=2, padx=(20, 40), pady=(4, 0))

        lf_main.grid(row=0, padx=30, pady=15)
        lf_advanced.grid(row=1, padx=30, pady=0, sticky=tk.W + tk.E)

        buttons_frame = ttk.Frame()
        self.restore_button = ttk.Button(buttons_frame, text=self.loc.text("Restore defaults"), command=self.restore_defaults)
        self.restore_button.grid(row=0, column=1, padx=(10, 0), pady=(20, 20))
        cancel_button = ttk.Button(buttons_frame, text=self.loc.text("Close without saving"), command=self.close_without_saving)
        cancel_button.grid(row=0, column=2, padx=10, pady=(20, 20))
        self.ok_button = ttk.Button(buttons_frame, text=self.loc.text("Save and close"), command=self.save_and_close, default=tk.ACTIVE)
        self.ok_button.grid(row=0, column=3, sticky=tk.W, padx=0, pady=(20, 20))
        buttons_frame.grid(row=100, columnspan=3)

        target_h, target_y = (600, 500)
        window_x = round((self.winfo_screenwidth() / 2) - (target_h / 2))
        window_y = round((self.winfo_screenheight() / 2) - (target_y / 2)) - 40
        master.geometry(f'+{window_x}+{window_y}')
        self.log.debug(f"Window position: {(window_x, window_y)}")

        self.update_default_button_state()
        master.update()
        self.window_dimensions = master.winfo_width(), master.winfo_height()
        self.log.debug(f"Window size: {self.window_dimensions}")

        # move window to the top (but don't keep it there)
        master.lift()
        master.attributes('-topmost', True)
        master.after_idle(master.attributes, '-topmost', False)

        if not gc.isenabled():
            gc.enable()
            gc.collect()
            self.log.debug("Enabled GC and collected")

    def __repr__(self):
        return f"settings.GUI {self.window_dimensions}"

    # runs every time a setting is changed, updates "restore defaults" button's state
    def update_default_button_state(self):
        if self.get_working_settings() == get_setting_default(return_all=True):  # if settings are default, disable button
            self.restore_button.state(['disabled'])
            self.log.debug("Disabled restore defaults button")
        else:
            self.restore_button.state(['!disabled'])
            self.log.debug("Enabled restore defaults button")

    # return the settings as a dict, as they currently are in the GUI
    def get_working_settings(self) -> dict:
        return {'sentry_level': self.sentry_levels[self.sentry_levels_display.index(self.sentry_level.get())],
                'wait_time': self.wait_time.get(),
                'map_invalidation_hours': self.map_invalidation_hours.get(),
                'check_updates': self.check_updates.get(),
                'request_timeout': max(self.request_timeout.get(), 1),
                'hide_queued_gamemode': self.hide_queued_gamemode.get(),
                'log_level': self.log_levels[self.log_levels_display.index(self.log_level.get())],
                'console_scan_kb': self.console_scan_kb.get(),
                'class_pic_type': self.class_pic_types[self.class_pic_types_display.index(self.class_pic_type.get())],
                'language': self.languages[self.languages_display.index(self.language.get())],
                'map_time': self.map_time.get(),
                'trim_console_log': self.trim_console_log.get()}

    # set all settings to defaults
    def restore_defaults(self):
        # TODO: fix unselected radio buttons when the displayed language != English
        settings_to_save = self.get_working_settings()
        settings_changed = {k: settings_to_save[k] for k in settings_to_save if k in self.settings_loaded and settings_to_save[k] != self.settings_loaded[k]}  # haha what

        settings_changed_num = len(settings_changed)
        allowed_reset = "yes"
        if settings_changed_num == 1:
            allowed_reset = messagebox.askquestion(self.loc.text("Restore defaults"), self.loc.text("Restore 1 changed setting to default?"))
        elif settings_changed_num > 1:
            allowed_reset = messagebox.askquestion(self.loc.text("Restore defaults"), self.loc.text("Restore {0} changed settings to defaults?").format(settings_changed_num))

        if allowed_reset == "yes":
            self.sentry_level.set(get_setting_default('sentry_level'))
            self.wait_time.set(get_setting_default('wait_time'))
            self.map_invalidation_hours.set(get_setting_default('map_invalidation_hours'))
            self.check_updates.set(get_setting_default('check_updates'))
            self.request_timeout.set(get_setting_default('request_timeout'))
            self.hide_queued_gamemode.set(get_setting_default('hide_queued_gamemode'))
            self.log_level.set(get_setting_default('log_level'))
            self.console_scan_kb.set(get_setting_default('console_scan_kb'))
            self.class_pic_type.set(get_setting_default('class_pic_type'))
            self.language.set(get_setting_default('language'))
            self.map_time.set(get_setting_default('map_time'))
            self.trim_console_log.set(get_setting_default('trim_console_log'))

            self.log.debug("Restored defaults")

            try:
                self.restore_button.state(['disabled'])
            except NameError:
                self.log.error("Restore button doesn't exist yet")

    # saves settings to file and closes window
    def save_and_close(self):
        # spinboxes can be set to blank, so if the user saves while blank, they try to default or be set to 0
        int_settings = self.wait_time, self.map_invalidation_hours, self.request_timeout, self.console_scan_kb
        for int_setting in int_settings:
            try:
                int_setting.get()
            except tk.TclError:
                int_setting.set(0)

        settings_to_save = self.get_working_settings()
        settings_changed = compare_settings(self.settings_loaded, settings_to_save)
        self.log.debug(f"Setting(s) changed: {settings_changed}")
        self.log.info("Saving and closing settings menu")
        access_registry(save_dict=settings_to_save)
        self.log.info(f"Settings have been saved as: {settings_to_save}")

        processes = str(subprocess.check_output('tasklist /fi "STATUS eq running"', creationflags=0x08000000))  # the creation flag disables a cmd window flash
        if 'Launch Rich Presence' in processes or 'Launch TF2 with Rich' in processes:
            restart_message = self.loc.text("TF2 Rich Presence is currently running, so it needs to be restarted for changes to take effect.")
        else:
            restart_message = ""

        settings_changed_num = len(settings_changed)
        if settings_changed_num == 1:
            messagebox.showinfo(self.loc.text("Save and close"), self.loc.text("1 setting has been changed. {0}").format(restart_message))
        elif settings_changed_num > 1:
            messagebox.showinfo(self.loc.text("Save and close"), self.loc.text("{0} settings have been changed. {1}").format(settings_changed_num, restart_message))

        self.master.destroy()  # closes window

    # closes window without saving
    def close_without_saving(self):
        settings_to_save = self.get_working_settings()
        settings_changed = compare_settings(self.settings_loaded, settings_to_save)
        self.log.debug(f"Setting(s) changed (but not yet saved): {settings_changed}")

        close_question = self.loc.text("Close without saving?")
        settings_changed_num = len(settings_changed)
        allowed_close = "yes"
        if settings_changed_num == 1:
            allowed_close = messagebox.askquestion(self.loc.text("Close without saving"), f"1 setting has been changed. {close_question}")
        elif settings_changed_num > 1:
            allowed_close = messagebox.askquestion(self.loc.text("Close without saving"), self.loc.text("{0} settings have been changed. {1}").format(settings_changed_num, close_question))

        if allowed_close == "yes":
            self.log.info("Closing settings menu without saving")
            self.master.destroy()

    # open the release page in the default browser
    def open_update_page(self):
        webbrowser.open(self.new_version_url)

    # called by atexit
    def window_close_log(self):
        self.log.info("Closing settings window")


# main entry point
def launch():
    gc.disable()
    root = tk.Tk()
    settings_gui = GUI(root)
    settings_gui.mainloop()


# access a setting from any file, with a string that is the same as the variable name (cached, so settings changes won't be rechecked right away)
@functools.lru_cache(maxsize=None)
def get(setting: str) -> Union[str, int, bool]:
    try:
        return access_registry()[setting]
    except KeyError:
        return get_setting_default(setting)


# either reads the settings key and returns it a a dict, or if a dict is provided, saves it
# note that settings are saved a JSON in a single string key
def access_registry(save_dict: Union[dict, None] = None) -> dict:
    reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\TF2 Rich Presence')

    try:
        reg_key_data = json.loads(winreg.QueryValue(reg_key, 'Settings'))
    except FileNotFoundError:  # means that the key hasn't been initialized
        # assume no key means default settings. might not be true but whatever
        default_settings = get_setting_default(return_all=True)
        winreg.SetValue(reg_key, 'Settings', winreg.REG_SZ, json.dumps(default_settings, separators=(',', ':')))
        reg_key_data = default_settings

    if save_dict:
        winreg.SetValue(reg_key, 'Settings', winreg.REG_SZ, json.dumps(save_dict, separators=(',', ':')))
    else:
        return reg_key_data


# either gets a settings default, or if return_dict, returns all defaults as a dict
def get_setting_default(setting: str = '', return_all: bool = False) -> Union[str, int, bool, dict]:
    defaults = {'sentry_level': 'All errors',
                'wait_time': 2,
                'map_invalidation_hours': 24,
                'check_updates': True,
                'request_timeout': 5,
                'hide_queued_gamemode': False,
                'log_level': 'Debug',
                'console_scan_kb': 1000,
                'class_pic_type': 'Icon',
                'language': 'English',
                'map_time': True,
                'trim_console_log': True}

    if return_all:
        return defaults
    else:
        return defaults[setting]


# checks if a string is an integer between 0 and a supplied maximum (blank is allowed, will get set to default when saving)
def check_int(text_in_entry: str, maximum: int) -> bool:
    if text_in_entry == '':
        return True

    if text_in_entry.isdigit() and 0 <= int(text_in_entry) <= float(maximum):
        return True

    return False


# find settings that are different between two settings dicts
def compare_settings(before: dict, after: dict) -> dict:
    return {k: after[k] for k in before if before[k] != after[k]}


# fixes settings that aren't in "current" from "default"
def fix_missing_settings(default: dict, current: dict) -> dict:
    missing_settings: dict = {}

    if len(default) != len(current):
        for default_setting in default:
            if default_setting not in current:
                missing_settings[default_setting] = default[default_setting]
                current[default_setting] = default[default_setting]

        access_registry(save_dict=current)

    return missing_settings


if __name__ == '__main__':
    launch()
