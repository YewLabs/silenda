function PuzzleSession(url) {
    var seq = 0;
    var session_id = null;

    var has_outstanding_req = false;

    var outstanding_params = null;
    var outstanding_callback = null;

    this.json_request = function(params, callback) {
        if (has_outstanding_req) {
            throw (new Error("Cannot have more than one outstanding request."));
        }
        has_outstanding_req = true;

        params.seq = seq;
        if (seq > 0) {
            params.session_id = session_id;
        }

        outstanding_params = params;
        outstanding_callback = function(res) {
            if (seq == 0) {
                session_id = res.session_id;
            }
            seq++;
            has_outstanding_req = false;
            callback(res);
        };
        ajax_until_success();
    };

    var ajax_is_out = false;

    function ajax_until_success() {
        ajax_is_out = true;
        $.ajax({
            type: "POST",
            url: url,
            dataType: "json",
            data: outstanding_params
        }).done(function(res) {
            ajax_is_out = false;
            if (res.query_success !== "true") {
                die();
            } else {
                outstanding_callback(res);
            }
        }).error(function() {
            ajax_is_out = false;
            displayConnectionError();
        });
    }

    function displayConnectionError() {
        connectionErrorMsg.show();
    }

    connectionRetryButton.on('click', function() {
        if (!ajax_is_out && has_outstanding_req) {
            ajax_until_success();
        }
    });

    function die() {
        dieErrorMsg.show();
    }

    return this;
}

var connectionErrorMsg = $('<div id="connection-error-message">Connection lost. <input type="button" value="Retry" id="connection-retry-button" /></div>');
connectionErrorMsg.css('font-weight: bold');
var dieErrorMsg = $('<div id="die-error-message">Unexpected error. This is not part of the puzzle. Please reload the page and try again.</div>');
dieErrorMsg.css('color', 'red');
dieErrorMsg.css('font-weight', 'bold');

var errorMsgContainer = $('#puzzle-session-error-message-container');
errorMsgContainer.append(connectionErrorMsg);
errorMsgContainer.append(dieErrorMsg);
errorMsgContainer.css('display', 'block');
errorMsgContainer.css('height', '60px');
errorMsgContainer.css('font-size', '24px');

connectionErrorMsg.hide();
dieErrorMsg.hide();

var connectionRetryButton = connectionErrorMsg.find("#connection-retry-button");
connectionRetryButton.on('click', function() {
    connectionErrorMsg.hide();
});
