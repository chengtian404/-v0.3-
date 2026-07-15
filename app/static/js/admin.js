;(function () {
    'use strict';

    function escapeHtml(value) {
        var node = document.createElement('div');
        node.textContent = value == null ? '' : String(value);
        return node.innerHTML;
    }

    function xsrfToken() {
        var input = document.querySelector('input[name="_xsrf"]');
        if (input) return input.value;
        var match = document.cookie.match(/(?:^|; )_xsrf=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function installNavigation() {
        var nav = document.querySelector('.layui-nav-tree');
        if (!nav) return;
        var groups = [
            {
                title: '数据瞭望子系统',
                items: [
                    ['/admin/observatory', 'layui-icon-search', '瞭望采集'],
                    ['/admin/sources', 'layui-icon-link', '瞭源管理'],
                    ['/admin/warehouse', 'layui-icon-table', '数据仓库']
                ]
            },
            {
                title: '模型引擎子系统',
                items: [
                    ['/admin/model-engine', 'layui-icon-engine', '模型引擎']
                ]
            }
        ];
        groups.forEach(function (group) {
            var missing = group.items.some(function (item) {
                return !nav.querySelector('a[href="' + item[0] + '"]');
            });
            if (!missing) return;
            var header = document.createElement('li');
            header.className = 'admin-nav-section';
            header.textContent = group.title;
            nav.appendChild(header);
            group.items.forEach(function (item) {
                if (nav.querySelector('a[href="' + item[0] + '"]')) return;
                var li = document.createElement('li');
                li.className = 'layui-nav-item';
                li.innerHTML = '<a href="' + item[0] + '"><i class="layui-icon ' +
                    item[1] + '"></i> ' + item[2] + '</a>';
                nav.appendChild(li);
            });
        });
        var path = window.location.pathname.replace(/\/$/, '') || '/';
        nav.querySelectorAll('.layui-nav-item').forEach(function (item) {
            item.classList.remove('layui-this');
            var link = item.querySelector('a[href]');
            if (link && link.getAttribute('href').replace(/\/$/, '') === path) {
                item.classList.add('layui-this');
            }
        });
    }

    function updateClock() {
        var el = document.getElementById('live-clock');
        if (!el) return;
        el.textContent = new Date().toLocaleString('zh-CN', {hour12: false});
    }

    document.addEventListener('DOMContentLoaded', function () {
        installNavigation();
        updateClock();
        window.setInterval(updateClock, 1000);
    });

    window.AdminUI = {
        escapeHtml: escapeHtml,
        xsrfToken: xsrfToken
    };
})();
