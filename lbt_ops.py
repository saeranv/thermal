"Jump to float doc
" inoremap <expr> <Leader>t coc#pum#visible() ?
"   \"\<C-r>=coc#pum#confirm()\<CR>\<Esc>:call ShowJumpeIntoDoc()\<CR>" : ""
" Scroll float doc
inoremap <nowait><expr> <C-j> coc#float#has_float() ? "\<c-r>=coc#float#scroll(1)\<cr>" : "\<Down>"
inoremap <nowait><expr> <C-k> coc#float#has_float() ? "\<c-r>=coc#float#scroll(0)\<cr>" : "\<Up>"
" Closing float doc
inoremap <expr> <Esc> coc#pum#visible() ? "\<Esc>:x\<CR>" : "\<Esc>"
inoremap <expr> <Esc> coc#float#has_float() ? "\<Esc>:x\<CR>" : "\<Esc>"
" COMMENTARY: use <leader>i<textobject> to apply; <leader>ii takes count
" Remove the default gc keybinding to no-op.
xmap <silent> <leader>i  <Plug>Commentary
" nmap <Leader>i  <Plug>Commentary
omap <silent> <leader>i  <Plug>Commentary
nmap <silent> <leader>i <Plug>CommentaryLine
noremap gc <Nop>
noremap gcc <Nop>

" SEMSHI
let g:semshi#filetypes=['python']
" Movement by code tree
"Note:                gd is goto declaration of variable under cursor
nmap <leader>sg gd
nmap <leader>sr :Semshi rename<CR>
nmap <leader>sn :Semshi goto name next<CR>
nmap <leader>sm :Semshi goto name prev<CR>
nmap <leader>sc :Semshi goto class next<CR>
nmap <leader>sv :Semshi goto class prev<CR>
nmap <leader>sf :Semshi goto function next<CR>
nmap <leader>sg :Semshi goto function prev<CR>
" nnoremap <silent> <leader>vv :r!date '+%Y%m%d'
" nnoremap <silent> <leader>v :r!date '+%H%M'<CR>
" <C-r>=: insert result of expression at cursor while in insert mode
nnoremap <leader>vv i<C-R>=strftime("%Y%m%d")<CR><Esc>
nnoremap <leader>v i<C-R>=strftime("%H%M")<CR><Esc>
noremap <leader>x iX<ESC>j
noremap <leader>w iW<ESC>j

" JUPYTER VIA JUKIT
let g:jukit_shell_cmd = 'ipython3'
"    - Specifies the command used to start a shell in the output split. Can also be an absolute path. Can also be any other shell command, e.g. `R`, `julia`, etc. (note that output saving is only possible for ipython)
let g:jukit_terminal = 'tmux'
let g:jukit_auto_output_hist = 0
"   - If set to 1, will create an autocmd with event `CursorHold` to show saved ipython output of current cell in output-history split. Might slow down (n)vim significantly.
let g:jukit_use_tcomment = 0
"   - Whether to use tcomment plugin (https://github.com/tomtom/tcomment_vim) to comment out cell markers. If not, then cell markers will simply be prepended with `g:jukit_comment_mark`
let g:jukit_comment_mark = '#'
"   - See description of `g:jukit_use_tcomment` above
let g:jukit_mappings = 0
"   - If set to 0, none of the default function mappings (as specified further down) will be applied
let g:jukit_mappings_ext_enabled = "*"
"   - String or list of strings specifying extensions for which the mappings will be created. For example, `let g:jukit_mappings_ext_enabled=['py', 'ipynb']` will enable the mappings only in `.py` and `.ipynb` files. Use `let g:jukit_mappings_ext_enabled='*'` to enable them for all files.
let g:jukit_notebook_viewer = 'jupyter-notebook'
"   - Command to open .ipynb files, by default jupyter-notebook is used. To use e.g. vs code instead, you could set this to `let g:jukit_notebook_viewer = 'code'`
let g:jukit_convert_overwrite_default = -1
"   - Default setting when converting from .ipynb to .py or vice versa and a file of the same name already exists. Can be of [-1, 0, 1], where -1 means no default (i.e. you'll be prompted to specify what to do), 0 means never overwrite, 1 means always overwrite
let g:jukit_convert_open_default = -1
"   - Default setting for whether the notebook should be opened after converting from .py to .ipynb. Can be of [-1, 0, 1], where -1 means no default (i.e. you'll be prompted to specify what to do), 0 means never open, 1 means always open
let g:jukit_file_encodings = 'utf-8'
"   - Default encoding for reading and writing to files in the python helper functions
let g:jukit_venv_in_output_hist = 1
"   - Whether to also use the provided terminal command for the output history split when starting the splits using the JukitOUtHist command. If 0, the provided terminal command is only used in the output split, not in the output history split.

" LUA HEREDOC
" Needs to be and end of init.vim or else screws up formatting
lua << EOF
local map = vim.keymap.set
local function accept_word()
    vim.fn['copilot#Accept']("")
    local bar = vim.fn['copilot#TextQueuedForInsertion']()
    return vim.fn.split(bar, [[[ .]\zs]])[1]
end

local function accept_line()
    vim.fn['copilot#Accept']("")
    local bar = vim.fn['copilot#TextQueuedForInsertion']()
    return vim.fn.split(bar, [[[\n]\zs]])[1]
end

vim.g.copilot_no_tab_map = true
map(
  "i", "qe", 'copilot#Accept("<CR><ESC>")',
  { silent=true, expr=true }
)
-- Note: make sure to add 'replace_keycodes=false' Saeran
-- https://github.com/orgs/community/discussions/29817#discussioncomment-4217615
-- q b/c similiar position to Tab (same as intellisense completion)
map('i', 'qw', accept_line, {expr=true, remap=false, replace_keycodes=false})
map('i', 'qr', accept_word, {expr=true, remap=false, replace_keycodes=false})
EOF
import os
import shutil
import sys

try:
    import clr
except ImportError as e:  # No .NET being used
    print('Failed to import CLR. OpenStudio SDK is unavailable.\n{}'.format(e))

try:
    from honeybee_energy.config import folders
except ImportError as e:
    print('Failed to import honeybee_energy. '
          'OpenStudio SDK is unavailable.\n{}'.format(e))


def load_osm(osm_path):
    """Load an OSM file to an OpenStudio SDK Model object in the Python environment.

    Args:
        osm_path: The path to an OSM file to be loaded an an OpenStudio Model.

    Returns:
        An OpenStudio Model object derived from the input osm_path.

    Usage:

    .. code-block:: python

        from ladybug_rhino.openstudio import load_osm

        # load an OpenStudio model from an OSM file
        osm_path = 'C:/path/to/model.osm'
        os_model = load_osm(osm_path)

        # get the space types from the model
        os_space_types = os_model.getSpaceTypes()
        for spt in os_space_types:
            print(spt)
    """
    # check that the file exists and OpenStudio is installed
    assert os.path.isfile(osm_path), 'No OSM file was found at "{}".'.format(osm_path)
    ops = import_openstudio()

    # load the model object and return it
    os_path = ops.OpenStudioUtilitiesCore.toPath(osm_path)
    osm_path_obj = ops.Path(os_path)
    exist_os_model = ops.Model.load(osm_path_obj)
    if exist_os_model.is_initialized():
        return exist_os_model.get()
    else:
        raise ValueError(
            'The file at "{}" does not appear to be an OpenStudio model.'.format(
                osm_path
            ))


def dump_osm(model, osm_path):
    """Dump an OpenStudio Model object to an OSM file.

    Args:
        model: An OpenStudio Model to be written to a file.
        osm_path: The path of the .osm file where the OpenStudio Model will be saved.

    Returns:
        The path to the .osm file as a string.

    Usage:

    .. code-block:: python

        from ladybug_rhino.openstudio import load_osm, dump_osm

        # load an OpenStudio model from an OSM file
        osm_path = 'C:/path/to/model.osm'
        model = load_osm(osm_path)

        # get all of the SetpointManagers and set their properties
        setpt_managers = model.getSetpointManagerOutdoorAirResets()
        for setpt in setpt_managers:
            setpt.setSetpointatOutdoorLowTemperature(19)
            setpt.setOutdoorLowTemperature(12)
            setpt.setSetpointatOutdoorHighTemperature(16)
            setpt.setOutdoorHighTemperature(22)

        # save the edited OSM over the original one
        osm = dump_osm(model, osm_path)
    """
    # check that the model is the correct object type
    ops = import_openstudio()
    assert isinstance(model, ops.Model), \
        'Expected OpenStudio Model. Got {}.'.format(type(model))

    # load the model object and return it
    os_path = ops.OpenStudioUtilitiesCore.toPath(osm_path)
    osm_path_obj = ops.Path(os_path)
    model.save(osm_path_obj, True)
    return osm_path


def import_openstudio():
    """Import the OpenStudio SDK into the Python environment.

    Returns:
        The OpenStudio NameSpace with all of the modules, classes and methods
        of the OpenStudio SDK.

    Usage:

    .. code-block:: python

        from ladybug_rhino.openstudio import import_openstudio, dump_osm
        OpenStudio = import_openstudio()

        # create a new OpenStudio model from scratch
        os_model = OpenStudio.Model()
        space_type = OpenStudio.SpaceType(os_model)

        # save the Model to an OSM
        osm_path = 'C:/path/to/model.osm'
        osm = dump_osm(os_model, osm_path)
    """
    try:  # first see if OpenStudio has already been loaded
        import OpenStudio
        return OpenStudio
    except ImportError:
        # check to be sure that the OpenStudio CSharp folder has been installed
        compatibility_url = 'https://github.com/ladybug-tools/lbt-grasshopper/wiki/' \
            '1.4-Compatibility-Matrix'
        in_msg = 'Download and install the version of OpenStudio listed in the ' \
            'Ladybug Tools compatibility matrix\n{}.'.format(compatibility_url)
        assert folders.openstudio_path is not None, \
            'No OpenStudio installation was found on this machine.\n{}'.format(in_msg)
        assert folders.openstudio_csharp_path is not None, \
            'No OpenStudio CSharp folder was found in the OpenStudio installation ' \
            'at:\n{}'.format(os.path.dirname(folders.openstudio_path))
        _copy_openstudio_lib()

        # add the OpenStudio DLL to the Common Language Runtime (CLR)
        os_dll = os.path.join(folders.openstudio_csharp_path, 'OpenStudio.dll')
        clr.AddReferenceToFileAndPath(os_dll)
        if folders.openstudio_csharp_path not in sys.path:
            sys.path.append(folders.openstudio_csharp_path)
        import OpenStudio
        return OpenStudio


def _copy_openstudio_lib():
    """Copy the openstudiolib.dll into the CSharp folder.

    This is a workaround that is necessary because the OpenStudio installer
    does not install the CSharp bindings correctly.
    """
    # see if the CSharp folder already has everything it needs
    dest_file = os.path.join(folders.openstudio_csharp_path, 'openstudiolib.dll')
    if os.path.isfile(dest_file):
        return None

    # if not, see if the openstudio_lib_path has the file that needs to be copied
    base_msg = 'The OpenStudio CSharp path at "{}" lacks the openstudiolib.dll'.format(
        folders.openstudio_csharp_path)
    assert os.path.isdir(folders.openstudio_lib_path), \
        '{}\nand there is no OpenStudio Lib installed.'.format(base_msg)
    src_file = os.path.join(folders.openstudio_lib_path, 'openstudiolib.dll')
    assert os.path.isfile(src_file), \
        '{}\nand this file was not found at "{}".'.format(base_msg, src_file)

    # copy the DLL if it exists
    shutil.copy(src_file, dest_file)
