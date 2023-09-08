async function getLoggedUser() {
    await fetch('/api/v1/logged_user')
        .then((res) => {
            if (res.status == 200) {
                window.location.replace('/courses.html')
            }
            else {
            }
        })
        .catch((err) => {
            alert("Something went wrong. Error: " + err.toString())
        })
}

getLoggedUser()