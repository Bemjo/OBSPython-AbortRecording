#    Abort Recording for OBS Studio
#    Copyright (C) 2024 https://github.com/Bemjo/

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import os
import platform
import json
import ctypes
from ctypes.util import find_library
import obspython as obs



# UI Localization strings
abort_hotkey_default_name = 'Abort Recording'
obs_hotkey_setting_description = 'Abort Recording Hotkey Name'
description = '''Abort Recording

Aborts the current recording using a hotkey and sends the file to your local trash receptacle.

Adds a new hotkey in your OBS Settings: Abort Recording'''

description_c_lib_error = '''

ERROR: The OBS library could not be loaded. This script cannot run.'''

description_send2trash_error = '''

ERROR: You must manually install the python package send2trash, for example: python -m pip install -U send2trash'''

msgbox_title = 'Abort Recording'
msgbox_text = 'Do you want stop the recording and delete the files?'



try:
    obsapi = ctypes.CDLL(find_library("obs"))
    c_lib_loaded = True
except OSError as e:
    c_lib_loaded = False
    print(f'Failed to load obs library: {e}')

try:
    from send2trash import send2trash
    validated_send2trash = True
except ImportError as e:
    validated_send2trash = False
    print(f'Failed to import library send2trash: {e}')


##### CTypes definitions, required for using obs_enum_outputs in a python script
class ObsOutput(ctypes.Structure):
    pass

class ObsData(ctypes.Structure):
    pass

if c_lib_loaded:
    obsapi.obs_enum_outputs.argtypes = [ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ObsOutput)), ctypes.c_void_p]
    obsapi.obs_output_get_id.argtypes = [ctypes.POINTER(ObsOutput)]
    obsapi.obs_output_get_id.restype = ctypes.c_char_p
    obsapi.obs_output_get_name.argtypes = [ctypes.POINTER(ObsOutput)]
    obsapi.obs_output_get_name.restype = ctypes.c_char_p
    obsapi.obs_output_get_settings.argtypes = [ctypes.POINTER(ObsOutput)]
    obsapi.obs_output_get_settings.restype = ctypes.c_char_p
    obsapi.obs_output_get_settings.argtypes = [ctypes.POINTER(ObsOutput)]
    obsapi.obs_output_get_settings.restype = ctypes.POINTER(ObsData)
    obsapi.obs_data_get_json.argtypes = [ctypes.POINTER(ObsData)]
    obsapi.obs_data_get_json.restype = ctypes.c_char_p
    obsapi.obs_data_release.argtypes = [ctypes.POINTER(ObsData)]
    obsapi.obs_data_release.restype = None



platform_windows = platform.system().lower() == 'windows'
hotkey_id = obs.OBS_INVALID_HOTKEY_ID
aborting_recording = False
output_paths = set()
file_change_signal_handler = None



def validated_libraries():
    return (
        validated_send2trash
    )



def is_loaded():
    return c_lib_loaded and validated_libraries()



def on_windows():
    global platform_windows
    return platform_windows



# Returns the file path of a given output, returns None if a path cannot be determined
def get_output_path(output):
    path = None
    settings = obs.obs_output_get_settings(output)
    if settings:
        json_str = obs.obs_data_get_json(settings)
        if json_str:
            settings_dict = json.loads(json_str)
            if 'path' in settings_dict:
                path = settings_dict['path']
                if on_windows():
                    path = path.replace('/', '\\')

        obs.obs_data_release(settings)

    return path



# CDLL API Version of get_output_path
def c_get_output_path(output):
    path = None
    settings = obsapi.obs_output_get_settings(output)
    if settings:
        json_str = obsapi.obs_data_get_json(settings)
        if json_str:
            settings_dict = json.loads(json_str.decode('utf-8'))
            if 'path' in settings_dict:
                path = settings_dict['path']
                if on_windows():
                    path = path.replace('/', '\\')

        obsapi.obs_data_release(settings)

    return path

def c_get_output_id(output):
    output_id = obsapi.obs_output_get_id(output)
    return output_id.decode('utf-8') if output_id else None

def c_get_output_name(output):
    output_name = obsapi.obs_output_get_name(output)
    return output_name.decode('utf-8') if output_name else None

def enum_outputs(param, output):
    global output_paths

    if c_get_output_id(output) == 'ffmpeg_muxer':
        path = c_get_output_path(output)
        if path is not None:
            output_paths.add(path)
    return True

enum_callback = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ObsOutput))(enum_outputs)



def on_abort_recording_hotkey(pressed):
    global aborting_recording
    global output_paths

    if pressed and obs.obs_frontend_recording_active() and not aborting_recording:
        aborting_recording = True
        # enumerate the outputs now, to collect any extra outputs created from plugins that may not have been enumerable on recording start
        obsapi.obs_enum_outputs(enum_callback, None)

        if not output_paths:
            print('No output path keys, cannot determine recording files.')

        print('Stopping Recording.')
        obs.obs_frontend_recording_stop()



def validate_files(files_list):
    tmp_list = []
    for file in files_list:
        if os.path.isfile(file):
            tmp_list.append(file)

    return tmp_list



def on_file_changed(calldata):
    global output_paths
    path = obs.calldata_string(calldata, 'next_file')
    if on_windows():
        path = path.replace('/', '\\')
    output_paths.add(path)



def on_recording(event):
    global file_change_signal_handler
    global aborting_recording
    global output_paths

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        output = obs.obs_frontend_get_recording_output()
        path = get_output_path(output)

        if path is not None:
            output_paths.add(path)
        
        if not file_change_signal_handler:
            file_change_signal_handler = obs.obs_output_get_signal_handler(output)

        obs.signal_handler_connect(file_change_signal_handler, 'file_changed', on_file_changed)
        obs.obs_output_release(output)

    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        if file_change_signal_handler:
            obs.signal_handler_disconnect(file_change_signal_handler, 'file_changed', on_file_changed)
            file_change_signal_handler = None

        if aborting_recording and output_paths:
            files_list = validate_files(output_paths)
            for file in files_list:
                try:
                    send2trash(file)
                    print(f'Sent {file} to trash')
                except Exception as e:
                    print(f'Unable to send file [{file}] to trash: {e}')

        aborting_recording = False
        output_paths.clear()



def script_description():
    global description
    global description_c_lib_error
    global description_send2trash_error
    global validated_send2trash
    global c_lib_loaded
    desc = description

    if not c_lib_loaded:
        desc = desc + description_c_lib_error

    if not validated_send2trash:
        desc = desc + description_send2trash_error

    if not validated_libraries():
        desc = desc  + '''

Please ensure the python modules are installed in one of the following paths:
'''

        for path in sys.path:
            if path:
                desc = desc + f'\n{path}'

    return desc



def script_properties():
    global obs_hotkey_setting_description
    props = obs.obs_properties_create()
    if is_loaded():
        obs.obs_properties_add_text(props, 'abort_recording_hotkey_name', obs_hotkey_setting_description, obs.OBS_TEXT_DEFAULT)

    return props



def script_defaults(settings):
    global abort_hotkey_default_name
    obs.obs_data_set_default_string(settings, 'abort_recording_hotkey_name', abort_hotkey_default_name)



def script_update(settings):
    global hotkey_id

    if is_loaded():
      obs.obs_hotkey_unregister(on_abort_recording_hotkey)
      hotkey_name = obs.obs_data_get_string(settings, 'abort_recording_hotkey_name')
      hotkey_id = obs.obs_hotkey_register_frontend("ABR/AbortRecordingHotkey", hotkey_name, on_abort_recording_hotkey)
      hotkey_save_array = obs.obs_data_get_array(settings, "abort_recording_hotkey")
      obs.obs_hotkey_load(hotkey_id, hotkey_save_array)
      obs.obs_data_array_release(hotkey_save_array)



def print_errors():
    global c_lib_loaded
    global validated_send2trash

    if not c_lib_loaded:
        print('Could not load the OBS C Library!')

    if not validated_send2trash:
        print('Could not import library send2trash, please manually install this package with pip for your python installation used by OBS.')
        print('Example: python -m pip install -U send2trash')

    if not validated_libraries():
        print('Please ensure these modules are located in one of the following folders')
        for path in sys.path:
            if path:
                print(f'\t{path}')



def script_load(settings):
    if is_loaded():
        obs.obs_frontend_add_event_callback(on_recording)
    else:
        print_errors()



def script_save(settings):
    global hotkey_id

    if is_loaded():
        hotkey_save_array = obs.obs_hotkey_save(hotkey_id)
        obs.obs_data_set_array(settings, 'abort_recording_hotkey', hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)



def script_unload():
    if is_loaded():
        obs.obs_frontend_remove_event_callback(on_recording)
