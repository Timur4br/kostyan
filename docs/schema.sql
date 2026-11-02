-- Reference schema generated from SQLAlchemy models. Do not apply over an existing database.


CREATE TABLE event_types (
	id SERIAL NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE locations (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE object_types (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	aliases TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE users (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE cameras (
	id SERIAL NOT NULL, 
	location_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	resolution VARCHAR(30) NOT NULL, 
	fps INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id)
)

;


CREATE TABLE objects (
	id VARCHAR(50) NOT NULL, 
	object_type_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	color VARCHAR(20) NOT NULL, 
	demo_x INTEGER NOT NULL, 
	demo_y INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(object_type_id) REFERENCES object_types (id)
)

;


CREATE TABLE search_history (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	query VARCHAR(300) NOT NULL, 
	result_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_search_history_user_id ON search_history (user_id);

CREATE INDEX ix_search_history_created_at ON search_history (created_at);


CREATE TABLE video_segments (
	id SERIAL NOT NULL, 
	camera_id INTEGER NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	source_kind VARCHAR(30) NOT NULL, 
	storage_reference TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(camera_id) REFERENCES cameras (id)
)

;


CREATE TABLE events (
	id SERIAL NOT NULL, 
	object_id VARCHAR(50) NOT NULL, 
	camera_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	event_type_id INTEGER NOT NULL, 
	video_segment_id INTEGER NOT NULL, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	confidence FLOAT NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_detection UNIQUE (object_id, camera_id, observed_at), 
	FOREIGN KEY(object_id) REFERENCES objects (id), 
	FOREIGN KEY(camera_id) REFERENCES cameras (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id), 
	FOREIGN KEY(event_type_id) REFERENCES event_types (id), 
	FOREIGN KEY(video_segment_id) REFERENCES video_segments (id)
)

;

CREATE INDEX ix_events_camera_id ON events (camera_id);

CREATE INDEX ix_events_observed_at ON events (observed_at);

CREATE INDEX ix_events_object_id ON events (object_id);