CREATE TABLE t_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    salt VARCHAR(100) NOT NULL,
    user_type INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE t_user_settings (
    user_id INT PRIMARY KEY,
    token VARCHAR(512) NOT NULL,
    save_video_path VARCHAR(256),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    FOREIGN KEY (user_id) REFERENCES t_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE t_video_task_execution (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    task_id VARCHAR(255) UNIQUE,
    prompt TEXT,
    model VARCHAR(100),
    model_supply VARCHAR(100),
    ratio VARCHAR(50),
    video_duration INT NOT NULL,
    video_nums INT,
    task_status VARCHAR(50),
    video_url VARCHAR(1024),
    failed_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_task_id (task_id),
    INDEX idx_video_duration (video_duration),
    FOREIGN KEY (user_id) REFERENCES t_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;