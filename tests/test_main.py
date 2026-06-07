from unittest.mock import patch

from notaris.__main__ import main


def test_main():
    with patch("notaris.__main__.uvicorn.run") as mock_run:
        main()
        mock_run.assert_called_once_with(
            "notaris.web.app:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
        )
