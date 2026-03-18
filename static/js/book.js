
function submitComment(bookId){
    const text = document.getElementById('commentInput').value;
    fetch(`/book/${bookId}/ajax/comment/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRF()},
        body: new URLSearchParams({text})
    })
    .then(res => res.json())
    .then(data => {
        const div = document.createElement('div');
        div.className = 'border p-2 mb-2';
        div.innerText = data.text;
        document.getElementById('commentList').prepend(div);
        document.getElementById('commentInput').value='';
    });
}

function submitRating(bookId, score){
    fetch(`/book/${bookId}/ajax/rating/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRF()},
        body: new URLSearchParams({score})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('avgRating').innerText = data.avg;
    });
}

function getCSRF(){
    return document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken'))
      ?.split('=')[1];
}
