document.addEventListener("DOMContentLoaded", function () {


    // ========================================================
    // LIKE / UNLIKE
    // ========================================================

    document.querySelectorAll(".like-button").forEach(function (button) {

        button.addEventListener("click", function () {

            const postId = button.dataset.postId;

            fetch("/like/" + postId, {
                method: "POST"
            })

            .then(function (response) {
                return response.json();
            })

            .then(function (data) {

                if (!data.success) {

                    alert(
                        data.message ||
                        "Unable to like this post."
                    );

                    return;
                }


                const count =
                    button.querySelector(".like-count");


                if (count) {
                    count.textContent = data.likes;
                }


                if (data.liked) {

                    button.classList.add("liked");

                    button.innerHTML =
                        "♥ Like " +
                        "<span class='like-count'>" +
                        data.likes +
                        "</span>";

                } else {

                    button.classList.remove("liked");

                    button.innerHTML =
                        "♡ Like " +
                        "<span class='like-count'>" +
                        data.likes +
                        "</span>";
                }

            })

            .catch(function () {

                alert(
                    "Something went wrong. Please try again."
                );

            });

        });

    });



    // ========================================================
    // FOLLOW / UNFOLLOW
    // ========================================================

    document.querySelectorAll(".follow-btn[data-user-id]")
    .forEach(function (button) {

        button.addEventListener("click", function () {

            const userId =
                button.dataset.userId;


            const isFollowing =
                button.classList.contains("following");


            const endpoint =
                isFollowing
                    ? "/unfollow/" + userId
                    : "/follow/" + userId;


            fetch(endpoint, {
                method: "POST"
            })

            .then(function (response) {
                return response.json();
            })

            .then(function (data) {

                if (!data.success) {

                    alert(
                        data.message ||
                        "Unable to update follow status."
                    );

                    return;
                }


                if (data.following) {

                    button.textContent = "Following";

                    button.classList.add("following");

                } else {

                    button.textContent = "Follow";

                    button.classList.remove("following");

                }

            })

            .catch(function () {

                alert(
                    "Something went wrong. Please try again."
                );

            });

        });

    });



    // ========================================================
    // COMMENT FOCUS
    // ========================================================

    document.querySelectorAll(".comment-toggle")
    .forEach(function (button) {

        button.addEventListener("click", function () {

            const card =
                button.closest(".post-card");


            if (!card) {
                return;
            }


            const input =
                card.querySelector(".comment-form input");


            if (input) {

                input.focus();

                input.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });

            }

        });

    });



    // ========================================================
    // AUTO RESIZE TEXTAREA
    // ========================================================

    document.querySelectorAll("textarea")
    .forEach(function (textarea) {

        textarea.addEventListener("input", function () {

            textarea.style.height = "auto";

            textarea.style.height =
                textarea.scrollHeight + "px";

        });

    });

});