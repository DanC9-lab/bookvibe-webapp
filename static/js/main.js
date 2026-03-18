/**
 * BookVibe front-end interactivity:
 * 1. AJAX rating submission
 * 2. AJAX comment submission
 * 3. AI chat interaction with quick prompts
 */

document.addEventListener('DOMContentLoaded', function () {
    const ratingForm = document.getElementById('rating-form');
    const commentForm = document.getElementById('comment-form');
    const chatForm = document.getElementById('chat-form');

    document.querySelectorAll('form[data-confirm]').forEach((form) => {
        form.addEventListener('submit', function (event) {
            const message = form.dataset.confirm || 'Are you sure?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll('.js-score-ring').forEach((ring) => {
        const scoreDeg = Number(ring.dataset.scoreDeg || 0);
        ring.style.setProperty('--score-deg', `${scoreDeg}deg`);
    });

    if (ratingForm) {
        ratingForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(ratingForm);
            const url = ratingForm.getAttribute('action');
            const csrfToken = formData.get('csrfmiddlewaretoken');

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': csrfToken },
            })
                .then((response) => response.json())
                .then((data) => {
                    if (!data.success) {
                        console.error('Rating submission failed:', data.errors);
                        return;
                    }

                    const avgEl = document.getElementById('average-rating-value');
                    const avgCopyEl = document.getElementById('average-rating-copy');
                    const countEl = document.getElementById('rating-count');
                    const msgEl = document.getElementById('rating-success-message');
                    const userRatingEl = document.getElementById('user-rating-display');
                    const scoreRing = document.querySelector('.js-score-ring');
                    const averageRating = Number(data.new_average_rating).toFixed(1);

                    if (avgEl) {
                        avgEl.textContent = averageRating;
                    }
                    if (avgCopyEl) {
                        avgCopyEl.textContent = `Community average ${averageRating} / 5`;
                    }
                    if (countEl) {
                        countEl.textContent = data.new_rating_count;
                    }
                    if (scoreRing) {
                        const scoreDeg = (Number(data.new_average_rating) / 5) * 360;
                        scoreRing.dataset.scoreDeg = String(scoreDeg);
                        scoreRing.style.setProperty('--score-deg', `${scoreDeg}deg`);
                    }
                    if (userRatingEl && data.user_rating) {
                        userRatingEl.innerHTML = `Your rating: <strong>${data.user_rating}/5</strong>`;
                    }
                    if (msgEl) {
                        msgEl.classList.remove('d-none');
                        setTimeout(() => msgEl.classList.add('d-none'), 2500);
                    }
                })
                .catch((error) => console.error('Rating network error:', error));
        });
    }

    if (commentForm) {
        commentForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(commentForm);
            const url = commentForm.getAttribute('action');
            const csrfToken = formData.get('csrfmiddlewaretoken');

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': csrfToken },
            })
                .then((response) => response.json())
                .then((data) => {
                    const commentList = document.getElementById('comment-list');
                    const countEl = document.getElementById('comment-count');
                    const noMsg = document.getElementById('no-comments-message');
                    const errorEl = document.getElementById('comment-error-message');

                    if (data.success) {
                        if (commentList) {
                            commentList.insertAdjacentHTML('afterbegin', data.comment_html);
                        }
                        commentForm.reset();
                        if (countEl) {
                            countEl.textContent = data.comment_count;
                        }
                        if (noMsg) {
                            noMsg.classList.add('d-none');
                        }
                        if (errorEl) {
                            errorEl.classList.add('d-none');
                            errorEl.textContent = '';
                        }
                    } else if (errorEl) {
                        const errorText = data.errors && data.errors.content ? data.errors.content[0] : 'An error occurred.';
                        errorEl.textContent = errorText;
                        errorEl.classList.remove('d-none');
                    }
                })
                .catch((error) => console.error('Comment network error:', error));
        });
    }

    if (chatForm) {
        const chatLog = document.getElementById('chat-log');
        const chatInput = document.getElementById('chat-message-input');
        const promptButtons = document.querySelectorAll('.js-chat-prompt');

        if (!chatLog || !chatInput || !chatForm.dataset.url) {
            return;
        }

        promptButtons.forEach((button) => {
            button.addEventListener('click', function () {
                chatInput.value = this.dataset.prompt;
                chatInput.focus();
            });
        });

        chatForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const userMessage = chatInput.value.trim();
            if (!userMessage) return;

            addMessageToLog(userMessage, 'user');
            chatInput.value = '';
            const typingEl = addMessageToLog('BookVibe AI is thinking...', 'ai', true);

            const formData = new FormData();
            formData.append('message', userMessage);
            formData.append('csrfmiddlewaretoken', chatForm.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(chatForm.dataset.url, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') },
            })
                .then((response) => response.json())
                .then((data) => {
                    typingEl.remove();
                    addMessageToLog(data.response || data.error || 'Sorry, something went wrong.', 'ai');
                })
                .catch((error) => {
                    typingEl.remove();
                    addMessageToLog('Sorry, I am having trouble responding right now. Please try again shortly.', 'ai');
                    console.error('Chat error:', error);
                });
        });

        function addMessageToLog(message, sender, isTyping = false) {
            const wrapper = document.createElement('div');
            wrapper.classList.add('chat-message', `${sender}-message`);
            const bubble = document.createElement('div');
            bubble.classList.add('message-bubble');
            if (isTyping) bubble.classList.add('typing-indicator');
            bubble.textContent = message;
            wrapper.appendChild(bubble);
            chatLog.appendChild(wrapper);
            chatLog.scrollTop = chatLog.scrollHeight;
            return wrapper;
        }
    }
});
