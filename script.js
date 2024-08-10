window.addEventListener('beforeunload', function () {
    fetch('/logout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `container_id=${container_id}`
    });
});
