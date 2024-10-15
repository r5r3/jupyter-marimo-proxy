#!/usr/bin/env python3

import os
import json
import glob
import base64
import secrets
import configparser
import logging


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def setup_marimoserver():

	token = secrets.token_urlsafe(16)
	newpath = os.environ.get('JUPYTERMARIMOPROXY_PATH')
	if not newpath:
		config = configparser.ConfigParser()
		config.read(os.path.expanduser(os.path.join('~', '.jupytermarimoproxyrc')))
		newpath = config.get('jupyter-marimo-proxy', 'path', fallback=config.get('DEFAULT', 'path', fallback=None))
	if newpath:
		seen = set()
		newpath = os.path.expandvars(os.pathsep.join(os.path.expanduser(x) for x in newpath.split(os.pathsep)))
		newpath = os.pathsep.join(x for x in newpath.split(os.pathsep) if x and x not in seen and not seen.add(x) and os.path.exists(x))

	def get_cwd_from_workspaces():
		"""
		use the latest change to ~/.jupyter/lab/workspaces/*.jupyterlab-workspace to get the current working directory
		"""
		default_cwd = os.environ.get('JUPYTER_SERVER_ROOT', os.getcwd())
		cwd = None
		workspace_dir = os.path.join(os.path.expanduser('~'), '.jupyter/lab/workspaces/')
		if os.path.exists(workspace_dir):
			workspace_file_paths = sorted(glob.glob(os.path.join(workspace_dir, '*.jupyterlab-workspace')), key=os.path.getmtime)
			if workspace_file_paths:
				with open(workspace_file_paths[-1], 'r') as workspace_file:
					try:
						workspace_data = json.load(workspace_file)
						if 'file-browser-filebrowser:cwd' in workspace_data['data']:
							cwd = workspace_data['data']['file-browser-filebrowser:cwd']['path']
					except (json.JSONDecodeError, KeyError) as e:
						logger.error(f"Error: unable to parse {workspace_file_paths[-1]}: {str(e)}")
		# if cwd is not absolute, join it with the root
		if cwd is not None and not os.path.isabs(cwd):
			cwd = os.path.join(default_cwd, cwd)
		if cwd is None or not os.path.exists(cwd):
			cwd = default_cwd
		print(f'Marimo: Using current working directory: {cwd}')
		return cwd

	def get_command():
		"""
		construct the command to run marimo
		"""
		result = ['marimo', 'edit', '--port', '{port}', '--base-url', os.environ['JUPYTERHUB_SERVICE_PREFIX'] + 'marimo', '--token', '--token-password', token, '--headless', get_cwd_from_workspaces()]
		logger.debug(f'Marimo: command: {result}')
		return result

	return {
		'command': get_command,
		'environment': { 'PATH': newpath } if newpath else {},
		'timeout': 60,
		'absolute_url': True,
		'request_headers_override': { 'Authorization': 'Basic ' + base64.b64encode(b' :' + token.encode()).decode() },
		'launcher_entry': {
			'title': 'Marimo',
			'icon_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.svg')
		},
	}
