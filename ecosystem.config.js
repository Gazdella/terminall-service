module.exports = {
    apps: [
        {
            name: "terminal-service",
            script: "app.py",
            interpreter: "./venv/bin/python",
            cwd: "./",
            instances: 1,
            autorestart: true,
            watch: false,
            max_memory_restart: "500M",
            env: {
                NODE_ENV: "production"
            },
            error_file: "./logs/terminal-error.log",
            out_file: "./logs/terminal-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss",
            merge_logs: true
        }
    ]
};
