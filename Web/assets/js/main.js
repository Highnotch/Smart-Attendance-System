
async function login(event) {
    event.preventDefault()

    const email = document.getElementsByName('email')[0].value
    const password = document.getElementsByName('password')[0].value
    const is_instructor = document.querySelectorAll('#choice-btn-container>div')[0].style.color == 'black' ? true : false


    let res = await fetch('/api/v1/login', {
        method: 'POST',
        body: JSON.stringify({ email: email, password: password, is_instructor: is_instructor }),
        headers: {
            'Content-Type': 'application/json'
        }
    })

    if (res.status == 200) {
        window.location.href = '/courses.html'
    } else {
        res = await res.json()
        document.getElementsByClassName('error-message')[0].innerHTML = res.message
    }
}

async function signup(event) {
    event.preventDefault()

    const email = document.getElementsByName('email')[0].value
    const name = document.getElementsByName('name')[0].value
    const password = document.getElementsByName('password')[0].value
    const is_instructor = document.querySelectorAll('#choice-btn-container>div')[0].style.color == 'black' ? true : false


    let res = await fetch('/api/v1/signup', {
        method: 'POST',
        body: JSON.stringify({ email: email, password: password, name: name, is_instructor: is_instructor }),
        headers: {
            'Content-Type': 'application/json'
        }
    })

    if (res.status == 200) {
        window.location.href = '/courses.html'
    } else {
        res = await res.json()
        document.getElementsByClassName('error-message')[0].innerHTML = res.message
    }
}


(function ($) {
    "use strict";


    /*==================================================================
   [ Focus input ]*/
    $('.input100').each(function () {
        $(this).on('blur', function () {
            if ($(this).val().trim() != "") {
                $(this).addClass('has-val');
            }
            else {
                $(this).removeClass('has-val');
            }
        })
    })


    /*==================================================================
    [ Validate ]*/
    var input = $('.validate-input .input100');

    $('.validate-form-signup').on('submit', function (event) {
        var check = true;

        for (var i = 0; i < input.length; i++) {
            if (validate(input[i]) == false) {
                showValidate(input[i]);
                check = false;
            }
        }
        if (check) signup(event)
        return check;
    });

    $('.validate-form').on('submit', function (event) {
        var check = true;

        for (var i = 0; i < input.length; i++) {
            if (validate(input[i]) == false) {
                showValidate(input[i]);
                check = false;
            }
        }
        if (check) login(event)
        return check;
    });


    $('.validate-form .input100').each(function () {
        $(this).focus(function () {
            hideValidate(this);
        });
    });

    function validate(input) {
        if ($(input).val().trim() == '') {
            return false;
        }
        return true

    }

    function showValidate(input) {
        var thisAlert = $(input).parent();

        $(thisAlert).addClass('alert-validate');
    }

    function hideValidate(input) {
        var thisAlert = $(input).parent();

        $(thisAlert).removeClass('alert-validate');
    }



})(jQuery);