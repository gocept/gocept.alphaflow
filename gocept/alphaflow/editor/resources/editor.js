function Editor() {
    this.sidebar = getElement('sidepane');
    this.baseURL = this.sidebar.getAttribute('base');
    this.mode = this.sidebar.getAttribute('mode');

    this.context = '';

    this.zoom = 2;
    this.canvas = getElement('graph');
    this.canvas_img = getElement('graphImage');
    new Draggable('graphImage', {starteffect:null});
    this.canvas_url = this.canvas_img.src;
    this.map = $('map');

    this.loadActivityPanel();

    connect('title', 'onclick', this, 'loadActivityPanel');
    connect('zoomIn', 'onclick', this, 'zoomIn');
    connect('zoomOut', 'onclick', this, 'zoomOut');
    connect('add-activity-menu', 'onchange', this, '_dispatch_selection');
    connect('use-template-menu', 'onchange', this, '_dispatch_selection');
    connect('use-groups-menu', 'onchange', this, '_dispatch_selection');

    if (this.mode == 'readonly') {
        removeElement('add-activity-menu');
        removeElement('use-template-menu');
    };
};

var READONLY_FUNCTIONS_WHITELIST = new Array(
        'activity', 'edit', 'panel', 'close-group',
        'expand-group', 'close-all-groups');
var FIND_PROTOCOL = /^(.*):\/\//

/******************** Helper functions *****************************/

Editor.prototype._is_read_only = function(func) {
    // Tests whether a given parsed URL function is available in read-only
    // mode.
    return some(READONLY_FUNCTIONS_WHITELIST,
            function (x) { return x == func.protocol; });
};

Editor.prototype._fix_ie_position = function() {
    /* IE positioning sledge hammer */
    var window_size = getViewportDimensions();

    /* Fix the graph canvas */
    var canvas_position = elementPosition(this.canvas);
    var new_canvas_size =  new Dimensions(window_size.w-canvas_position.x-10,
                                          window_size.h-canvas_position.y-10);
    setElementDimensions(this.canvas, new_canvas_size, 'px');

    /* Fix the side pane */
    var sidebar_size = elementDimensions(this.sidebar);
    var sidebar_position = elementPosition(this.sidebar);
    var sidebar_size = new Dimensions(
        sidebar_size.w,
        window_size.h-canvas_position.y-10);
    setElementDimensions(this.sidebar, sidebar_size, 'px');
}

Editor.prototype._do_request = function(path, query, callback) {
    var editor = this;

    var url = editor.baseURL + '/' + path;
    if (query == null) {
        query = {};
    }
    var d = doSimpleXMLHttpRequest(url, query);
    d.addCallbacks(callback, log);
    return d;
}

Editor.prototype._loadPanel = function(panel, query) {
    var editor = this;
    return editor._do_request(panel, query, 
        function(result) {
            editor.sidebar.innerHTML = result.responseText;
            editor._parse_panel_links(result);
            editor._connect_panel_buttons(result);
            editor.reloadCanvas();
            return result;
        });
};


Editor.prototype._submit_form = function(form, callback) {
    /* Generic helper function for submitting a form. */
    var form = getElement(form);
    var data = map(function(element) {
            return element.name + "=" + encodeURIComponent(element.value)
        }, form.elements);
    data = data.join('&');
    var d = doXHR(form.getAttribute('action'), {
        'method': 'POST',
        'headers': {
            'Content-Type': 'application/x-www-form-urlencoded'},
        'sendContent': data});
    d.addCallbacks(callback, log);
}

function toArray(obj) {
  /* Converts an iterable obj to an aray */
  var result = new Array();
  for (var i = 0; i < obj.length; i++) {
      result.push(obj[i]);
  };
  return result;
}

/* General button activation
 *
 * all buttons are found in the loaded HTML and connected to editor functions that
 * have the same name as the button
 */

Editor.prototype._connect_panel_buttons = function(result) {
    var editor = this;

    buttons = getElementsByTagAndClassName('input');

    forEach(buttons, function(button) {
            if (button.getAttribute('type') != 'button') {
                return;
            };
            if (editor.mode == 'readonly') {
                removeElement(button);
            } else {
                connect(button, 'onclick', editor, button.getAttribute('id'));
            };
            });
}

/* General link parsing.

   I use special protocol names to mark up loading certain panels. This is the
   generalization.

*/

Editor.prototype._parse_url = function(url) {
    var protocols = Array(
        Array("activity", "loadActivityDetailsPanel"),
        Array('add-activity', 'addActivity'),

        Array("edit", "loadEditPanel"),
        Array("panel", "_loadPanel"),
        Array("delete", "deleteObject"),

        Array("close-group", "closeGroup"),
        Array("expand-group", "expandGroup"),
        Array("close-all-groups", "closeAllGroups"),

        Array("new-exit", "addExit"),
        Array("new-permission-setting", "addPermissionSetting"));

    /* Parse a URL into a function and their arguments and return them. */
    var editor = this;
    var protocol_match = url.match(FIND_PROTOCOL);
    if (protocol_match == null) {
      return null;
    };
    var protocol = protocol_match[1];
    var args = url.replace(FIND_PROTOCOL, "");
    /* IE FIX. IE leaves a trailing slash. :/ */
    args = args.replace(/\/$/, "");
    args = args.split('/');

    var func = null;

    /* Translate the function name and get the function handle */
    if (protocol == 'call-function') {
        func = 'call-function';
    } else { 
        forEach(protocols, function(candidate) {
            if (protocol == candidate[0]) {
                func = editor[candidate[1]];
                func.protocol = candidate[0];
            }
        });
    }
    return new Array(func).concat(args);
}

Editor.prototype._parse_panel_links = function(result) {
    var editor = this;

    var a_links = getElementsByTagAndClassName('a');
    var area_links = getElementsByTagAndClassName('area');

    /* Special concatenation construction for IE 6. */
    var links = new Array();
    extend(links, a_links);
    extend(links, area_links);

    forEach(links, function(link) {
        var args = editor._parse_url(link.href);
        if (args == null) {
            return; /* continue */
        };
        var func = args.shift();

        if (func == 'call-function') {
            /* This is an immediate call */
            editor._dispatch_path_call(args);
        } else if (func != null) {
            link.href = "#";
            if (editor.mode == 'readonly' && !editor._is_read_only(func)) {
                // Do not set up functions that aren't marked valid for
                // read-only.
                removeElement(link);
                return;
            };
            connect(link, 'onclick', editor, function() {func.apply(editor, args);});
        }
    });
}


Editor.prototype.copyDataForSubmit = function(name) {
  /* Indirection to support our `href` model with `call-function` */
  copyDataForSubmit(name);
}

Editor.prototype._dispatch_path_call = function(args) {
    /* This function dispatches an argument list (e.g. as extracted from a path)
     * into a function call with arguments.
     *
     * The path: function/arg1/arg2/arg3 is translated into
     * Editor.function(arg1, arg2, arg3).
     */
    function_name = args.shift();
    editor[function_name].apply(editor, args);
};

Editor.prototype._dispatch_selection = function(event) {
    var editor = this;
    /* Dispatch an onChange event from a form element into a path call */
    var args = editor._parse_url(event.src().value);
    var func = args.shift();
    func.apply(editor, args);
    /* Reset the menu to its original state. */
    event.src().value = null;
};

Editor.prototype.submitForm = function() {
    var pane = this.sidebar;
    var editor = this;
    this._submit_form('zc.page.browser_form',
        function(result) {
            pane.innerHTML = result.responseText;
            editor._parse_panel_links();
            editor._connect_panel_buttons();
            editor.reloadCanvas();
        });
};


Editor.prototype.loadEditPanel = function() {
    /* This function takes any number of arguments and joins them as a path
     * relative to the workflow base url. */
    var editor = this;
    editor.context = toArray(arguments).join('/');
    var d = editor._loadPanel(editor.context+'/@@edit');
    return d;
};

/******************** Actual business functions ************************/

/* Activity listing */

Editor.prototype.loadActivityPanel = function() {
    var editor = this;
    editor.context = '';
    var d = editor._loadPanel('activitypanel');
};

Editor.prototype.addActivity = function(type) {
    var editor = this;
    this._do_request('add_activity', Array(Array('activity'), Array(type)),
        function(result) {editor.loadEditPanel(result.responseText);});
};

/* Delete something */

Editor.prototype.deleteObject = function() {
    var editor = this;
    editor.context = toArray(arguments).join('/');
    editor._do_request(editor.context+'/delete', null,
            function(result) {
                log(result);
                editor._dispatch_path_call(result.responseText.split('/'));
            });
};

/* Activity details */

Editor.prototype.loadActivityDetailsPanel = function(activity) {
    var editor = this;
    editor.context = activity;
    var d = editor._loadPanel(activity+'/activity_details');
    editor.reloadCanvas();
    return false;
};


/* Add a new aspect */

Editor.prototype.addAspect = function() {
    var editor = this;
    d = editor._submit_form('addAspectForm',
        function(result) {
            editor.loadEditPanel(result.responseText);
    });
};

/* Add a new exit */

Editor.prototype.addExit = function() {
    var editor = this;
    editor._do_request(editor.context+'/add_exit', null,
        function(result) {
        editor.loadEditPanel(result.responseText);
    });
}

/* Add a permission setting */
Editor.prototype.addPermissionSetting = function() {
    var editor = this;
    editor._do_request(editor.context+'/add_setting',
        null, function(result) {
        editor.loadEditPanel(result.responseText);
    });
}

/* Workflow graph */

Editor.prototype.reloadCanvas = function() {
    var editor = this;

    var query_names = ["zoom", "random", "highlight", "format"];
    var query_values = [editor.zoom, (new Date()).getTime(), editor.context, "png"];

    var query = queryString(query_names, query_values);

    editor.canvas_img.src = editor.canvas_url + '?' + query;

    /* Reload the image map */
    var url = editor.baseURL + '/@@map?' + query;
    var d = doSimpleXMLHttpRequest(url);
    d.addCallbacks(
        function(result) {
            editor.map.innerHTML = result.responseText;
            editor._parse_panel_links()
            editor.canvas_img.setAttribute('useMap', "#F");
            editor.canvas_img.setAttribute('useMap', "#G");
            return result;
        }, log);
}

Editor.prototype.zoomIn = function() {
    var editor = this;
    editor.zoom = editor.zoom + 1;
    editor.reloadCanvas()
}

Editor.prototype.zoomOut = function() {
    var editor = this;
    if (editor.zoom == 3) {
      return;
    };
    editor.zoom = editor.zoom - 1;
    editor.reloadCanvas()
}

/* Activity group management */

Editor.prototype.expandGroup = function (group) {
    var editor = this;
    this._do_request('expandGroup', Array(Array('groupname'), Array(group)), 
        function () {
            editor.reloadCanvas()
        });
};

Editor.prototype.closeGroup = function (group) {
    var editor = this;
    this._do_request('closeGroup', Array(Array('groupname'), Array(group)), 
        function () {
            editor.reloadCanvas()
        });
};

Editor.prototype.closeAllGroups = function () {
    var editor = this;
    this._do_request('closeAllGroups', null, function () {
            editor.reloadCanvas()
        });
};

Editor.prototype.addGroup = function() {
    var editor = this;
    editor._submit_form('addGroupForm', 
        function(result) {editor.loadActivityPanel();});
};

var editor;
connect(window, "onload", function(){
    editor = new Editor();
});
