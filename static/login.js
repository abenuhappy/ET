// 로그인 폼 처리
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('errorMessage');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password }),
        });

        const data = await response.json();

        if (response.ok) {
            // 로그인 성공 - 메인 페이지로 이동
            window.location.href = '/';
        } else {
            // 로그인 실패 - 에러 메시지 표시
            errorMessage.textContent = data.error || '로그인에 실패했습니다.';
            errorMessage.style.display = 'block';
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        }
    } catch (error) {
        errorMessage.textContent = '서버 오류가 발생했습니다.';
        errorMessage.style.display = 'block';
    }
});

// Enter 키로 로그인
document.getElementById('password').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('loginForm').dispatchEvent(new Event('submit'));
    }
});
