import single_instance
from main import APP_TITLE, TranslateApp


def main():
    if not single_instance.ensure_single(APP_TITLE):
        return
    app = TranslateApp(fixed_engine='offline')
    app.mainloop()


if __name__ == '__main__':
    main()
