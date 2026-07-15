(function () {
    "use strict";
    document.addEventListener("DOMContentLoaded", function () {
        document.body.classList.add("loaded");
    });
    window.confirmAction = function (message, callback) {
        if (window.confirm(message)) callback();
    };
})();
