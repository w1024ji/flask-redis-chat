from my_app import create_app, db, socketio
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    socketio.run(app, debug=False)

