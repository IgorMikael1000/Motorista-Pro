const IMGBB_API_KEY = '94e16d456f7d01e647d473dde2674677'; // <--- INSIRA SUA CHAVE AQUI

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileAvatar');
    const avatarImg = document.getElementById('avatarImg');
    const loadingSpinner = document.getElementById('avatarLoader');
    const avatarIcon = document.getElementById('avatarIcon');

    if (!fileInput) return;

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if(avatarImg) avatarImg.style.opacity = '0.5';
        if(avatarIcon) avatarIcon.style.opacity = '0.5';
        if(loadingSpinner) loadingSpinner.style.display = 'block';

        try {
            // 1. Comprimir
            const compressedFile = await compressImage(file);
            
            // 2. Upload para ImgBB
            const formData = new FormData();
            formData.append('image', compressedFile);

            const response = await fetch(`https://api.imgbb.com/1/upload?key=${IMGBB_API_KEY}`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const imageUrl = result.data.url;
                
                // 3. Salvar no Backend
                await saveToBackend(imageUrl);
                
                alert('Foto atualizada com sucesso!');
                // 4. Recarregar para atualizar em todo o app
                window.location.reload();
            } else {
                throw new Error('Falha no ImgBB: ' + (result.error ? result.error.message : 'Erro desconhecido'));
            }

        } catch (error) {
            console.error(error);
            alert('Erro ao enviar foto. Tente novamente.');
            if(avatarImg) avatarImg.style.opacity = '1';
            if(avatarIcon) avatarIcon.style.opacity = '1';
        } finally {
            if(loadingSpinner) loadingSpinner.style.display = 'none';
        }
    });
});

function compressImage(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = event => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const MAX_SIZE = 300;
                let width = img.width;
                let height = img.height;
                
                if (width > height) {
                    if (width > MAX_SIZE) { height *= MAX_SIZE / width; width = MAX_SIZE; }
                } else {
                    if (height > MAX_SIZE) { width *= MAX_SIZE / height; height = MAX_SIZE; }
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob(blob => { resolve(blob); }, 'image/jpeg', 0.8);
            };
            img.onerror = error => reject(error);
        };
        reader.onerror = error => reject(error);
    });
}

async function saveToBackend(url) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    await fetch('/update_avatar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ url: url })
    });
}



