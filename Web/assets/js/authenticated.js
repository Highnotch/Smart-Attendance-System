async function getLoggedUser() {
    await fetch('/api/v1/logged_user')
        .then((res) => {
            if (res.status == 200) { }
            else {
                window.location.replace('/login.html')
            }
        })
        .catch((err) => {
            alert("Something went wrong. Error: " + err.toString())
        })
}

getLoggedUser()